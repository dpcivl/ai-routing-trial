"""① 규칙(키워드) 기반 라우터.

동작 원리:
  1. 카테고리마다 "신호(패턴)" 목록과 가중치(weight)를 정해둡니다.
  2. 프롬프트에서 패턴이 발견될 때마다 해당 카테고리에 가중치만큼 점수를 더합니다.
  3. 점수가 가장 높은 카테고리를 고릅니다.
  4. 확신도 = 1등 점수 / 전체 점수 합
     예) coding 4점, reasoning 1점 → coding, 확신도 4/5 = 0.8

장점: 매우 빠르고(1ms 미만), 왜 그렇게 판단했는지 100% 설명 가능합니다.
단점: 목록에 없는 표현은 못 잡고, 문맥을 모릅니다.
      예) "파이썬(뱀)의 생태를 알려줘" → '파이썬' 때문에 coding으로 오판

한국어 참고:
  한국어는 "함수를", "함수가"처럼 조사가 붙으므로 \b(단어 경계)를 쓰면 매칭이 안 됩니다.
  그래서 한국어 패턴은 부분 문자열로, 영어 패턴은 \b로 감싸서 단어 단위로 찾습니다.
"""

import re
from dataclasses import dataclass

from ai_router.routers.base import Router
from ai_router.types import Category


@dataclass(frozen=True)
class Signal:
    pattern: str  # 정규표현식
    weight: float  # 발견 시 더할 점수
    label: str  # 판단 근거에 표시할 이름


def _en(*words: str, weight: float = 1.0) -> list[Signal]:
    """영어 단어용: 대소문자 무시 + 단어 경계(\\b) 적용."""
    return [Signal(rf"(?i)\b{re.escape(w)}\b", weight, w) for w in words]


def _ko(*words: str, weight: float = 1.0) -> list[Signal]:
    """한국어 단어용: 부분 문자열 매칭."""
    return [Signal(re.escape(w), weight, w) for w in words]


# -----------------------------------------------------------------------------
# 카테고리별 신호 목록
# 라우팅 결과 문서에서 오답이 나오면 이 목록을 고치고 다시 평가하는 식으로 개선합니다.
# -----------------------------------------------------------------------------
SIGNALS: dict[Category, list[Signal]] = {
    Category.CODING: [
        # 코드 모양 자체는 매우 강한 신호이므로 가중치를 높게 줍니다.
        Signal(r"```", 3.0, "코드 블록(```)"),
        Signal(r"Traceback \(most recent call last\)", 3.0, "파이썬 Traceback"),
        Signal(r"\b(def|class|import|return|void|int|#include)\s", 2.0, "코드 키워드"),
        Signal(r"\w+\([^)]*\)\s*[;{]", 2.0, "함수 호출/정의 모양"),
        *_ko(
            "코드",
            "함수",
            "버그",
            "디버깅",
            "컴파일",
            "리팩터링",
            "리팩토링",
            "구현",
            "변수",
            "클래스",
            "메서드",
            "에러",
            "오류",
            "예외",
            "테스트 코드",
            "알고리즘",
            "정규식",
            "쿼리",
            "스크립트",
        ),
        *_en(
            "code",
            "function",
            "bug",
            "debug",
            "compile",
            "refactor",
            "implement",
            "python",
            "javascript",
            "typescript",
            "java",
            "rust",
            "golang",
            "c++",
            "sql",
            "regex",
            "api",
            "error",
            "exception",
            "unit test",
            "script",
        ),
        *_ko("파이썬", "자바스크립트", "타입스크립트", "자바", "러스트", weight=1.5),
    ],
    Category.VISION: [
        # vision 카테고리 = 이미지 분석 + UI/UX 디자인 질문
        # (UI, UX는 영어 목록에서 대소문자 무시로 잡으므로 한국어 목록에 중복으로 넣지 않습니다)
        *_ko("이미지", "스크린샷", "사진", "그림", "캡처", "화면", "시안", weight=1.5),
        *_ko(
            "디자인",
            "레이아웃",
            "색상",
            "색감",
            "폰트",
            "배색",
            "여백",
            "와이어프레임",
            "아이콘",
            "로고",
            "배치",
        ),
        *_en(
            "image",
            "screenshot",
            "photo",
            "picture",
            "design",
            "layout",
            "color",
            "font",
            "wireframe",
            "mockup",
            "icon",
            "logo",
            "ui",
            "ux",
        ),
    ],
    Category.REASONING: [
        *_ko(
            "왜",
            "설명",
            "비교",
            "분석",
            "장단점",
            "차이",
            "추론",
            "논리",
            "계산",
            "요약",
            "정리",
            "전략",
            "계획",
            "판단",
            "어떻게 생각",
            "의견",
            "원리",
        ),
        *_en(
            "why",
            "explain",
            "compare",
            "analyze",
            "pros and cons",
            "difference",
            "reason",
            "logic",
            "calculate",
            "summarize",
            "strategy",
            "plan",
        ),
    ],
}


class RuleBasedRouter(Router):
    name = "rule"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 정규식은 미리 컴파일해 두면 매번 파싱하지 않아 빠릅니다.
        # (임베디드에서 룩업 테이블을 미리 만들어 두는 것과 같은 발상)
        self._compiled = {
            cat: [(re.compile(s.pattern), s) for s in signals] for cat, signals in SIGNALS.items()
        }

    def _classify(self, text: str) -> tuple[Category, float, str]:
        scores: dict[Category, float] = {cat: 0.0 for cat in Category}
        hits: dict[Category, list[str]] = {cat: [] for cat in Category}

        for cat, compiled in self._compiled.items():
            for regex, signal in compiled:
                if regex.search(text):
                    scores[cat] += signal.weight
                    hits[cat].append(signal.label)

        total = sum(scores.values())
        if total == 0:
            # 아무 신호도 없으면 확신도 0 → 부모 클래스가 기본 카테고리로 보냅니다.
            return self.default_category, 0.0, "매칭된 키워드 없음"

        best = max(scores, key=lambda c: scores[c])
        confidence = scores[best] / total
        summary = ", ".join(f"{cat}={scores[cat]:g}{hits[cat]}" for cat in Category if scores[cat] > 0)
        return best, confidence, summary
