"""③ 소형 LLM 분류기 라우터.

동작 원리:
  1. 작은 언어 모델(qwen3.5:2b 등)에게 "이 요청은 reasoning / coding / vision 중 무엇인가?"를 묻습니다.
  2. 모델이 카테고리 단어 하나로 답하면, 그 문자열을 파싱해서 Category로 바꿉니다.
  3. 답을 못 알아듣겠으면(빈 응답, 엉뚱한 답, 두 카테고리가 섞인 답) 확신도 0으로 처리해서
     부모 클래스(Router)가 기본 카테고리로 보내게 합니다.

규칙 기반과 비교:
  - 장점: 키워드에 없는 표현도 "의미"로 이해합니다. 예) "git에서 마지막 커밋 메시지 수정" → coding
          동음이의어도 문맥으로 구분합니다. 예) "파이썬(비단뱀)의 서식지" → reasoning
  - 단점: 느리고(수백 ms~수 초), 메모리를 쓰고(모델 로딩), 같은 입력에도 답이 흔들릴 수 있습니다.
          그리고 프롬프트(아래 SYSTEM_PROMPT)를 어떻게 쓰느냐에 성능이 크게 좌우됩니다.

확신도에 대한 한계:
  Ollama의 OpenAI 호환 API는 logprobs(각 후보 단어의 확률)를 지원하지 않습니다.
  그래서 "모델이 얼마나 확신하는가"를 숫자로 얻을 수 없습니다. 이 라우터는
    - 답을 명확히 파싱했으면 확신도 1.0
    - 못 했으면 확신도 0.0 (→ 기본 카테고리로 fallback)
  두 값만 씁니다. 따라서 --threshold 옵션은 이 라우터에서 사실상 의미가 없습니다.
  (개선 아이디어: 모델에게 확신도를 직접 말하게 하기 / 같은 질문을 여러 번 물어 다수결)

평가 데이터 오염(contamination) 주의:
  아래 프롬프트의 예시 문장은 data/eval/routing_v1.jsonl 의 문항과 겹치지 않게 따로 만든 것입니다.
  평가셋의 문장을 그대로 예시로 넣으면 "시험 문제를 미리 알려주는 것"이라 정확도가 부풀려집니다.
"""

import re

from ai_router.backends.base import ChatBackend
from ai_router.config import AppConfig, ModelConfig
from ai_router.routers.base import Router
from ai_router.types import Category

# 시스템 메시지: 모델의 역할과 규칙을 알려줍니다.
# 작은 모델은 영어 지시를 더 잘 따르는 경향이 있어 지시문은 영어로 쓰고, 예시는 한국어/영어를 섞었습니다.
SYSTEM_PROMPT = """You are a request router. Read the user's request and decide which specialist should handle it.
Reply with exactly ONE word from this list and nothing else: reasoning, coding, vision.

Definitions:
- coding: the user wants code written, fixed, explained line by line, refactored or tested; asks about programming tools, errors, stack traces, commands (git, docker, SQL, regex, etc.).
- vision: the request is about UI/UX or visual design (layout, colors, fonts, icons, logos, wireframes) or about looking at an image, screenshot or chart.
- reasoning: everything else: general knowledge, explanations, comparisons, analysis, math, planning, summaries, advice.

Rules:
- Decide by what the user wants DONE, not by single keywords. A word like "python" or "design" can appear in a request of any type.
- If the user asks for an explanation of a concept without asking for code, choose reasoning.

Examples:
Request: 배열에서 중복을 제거하는 자바스크립트 함수 작성해줘
Answer: coding
Request: Why is my Docker container exiting immediately?
Answer: coding
Request: 복리 이자가 어떻게 계산되는지 예를 들어 설명해줘
Answer: reasoning
Request: 두 나라의 교육 제도를 비교해서 장단점을 정리해줘
Answer: reasoning
Request: 앱 설정 화면의 버튼 색상 조합을 추천해줘
Answer: vision
Request: What spacing should I use between cards in a grid layout design?
Answer: vision"""

# 사용자 요청이 너무 길면 분류 시간이 늘어나므로 앞부분만 보냅니다. 카테고리 판단에는 앞부분으로 충분합니다.
MAX_INPUT_CHARS = 2000

_CATEGORY_WORDS = "|".join(c.value for c in Category)
_CATEGORY_RE = re.compile(rf"\b({_CATEGORY_WORDS})\b", re.IGNORECASE)
# 일부 모델은 <think>...</think> 안에 생각 과정을 적습니다. 그 안의 단어가 답으로 오인되면 안 됩니다.
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def parse_category(raw: str) -> tuple[Category | None, str]:
    """모델 출력 문자열에서 카테고리를 뽑아냅니다.

    반환: (카테고리 또는 None, 실패했을 때의 이유)
    - 카테고리 단어가 정확히 한 종류만 나오면 성공 ("coding", "Coding.", "**coding**" 모두 OK)
    - 하나도 없거나(빈 응답 포함) 서로 다른 단어가 둘 이상 나오면 실패
    """
    cleaned = _THINK_RE.sub("", raw).strip()
    if not cleaned:
        return None, "빈 응답 (생각 모드가 max_tokens를 다 쓴 경우일 수 있음)"
    found = {m.group(1).lower() for m in _CATEGORY_RE.finditer(cleaned)}
    if not found:
        return None, "카테고리 단어 없음"
    if len(found) > 1:
        return None, f"서로 다른 카테고리가 섞임: {sorted(found)}"
    return Category(found.pop()), ""


class LLMClassifierRouter(Router):
    name = "llm"

    def __init__(self, backend: ChatBackend, classifier: ModelConfig, **kwargs):
        super().__init__(**kwargs)
        self.backend = backend
        self.classifier = classifier

    @classmethod
    def from_config(cls, config: AppConfig, backend: ChatBackend, confidence_threshold: float):
        if config.router_llm is None:
            raise ValueError("configs/models.yaml 에 router_llm 항목이 없습니다. (--router llm 에 필요)")
        return cls(
            backend=backend,
            classifier=config.router_llm,
            default_category=config.default_category,
            confidence_threshold=confidence_threshold,
        )

    def _ask(self, text: str) -> str:
        result = self.backend.chat(
            model=self.classifier.name,
            # 요청을 구분선으로 감싸서 "이 내용에 답하라"가 아니라 "이 내용을 분류하라"로 읽히게 합니다.
            prompt=f'Request:\n"""\n{text[:MAX_INPUT_CHARS]}\n"""\nAnswer:',
            temperature=self.classifier.temperature,
            max_tokens=self.classifier.max_tokens,
            system=SYSTEM_PROMPT,
            extra_body=self.classifier.extra_body,
        )
        return result.text

    def _classify(self, text: str) -> tuple[Category, float, str]:
        raw = self._ask(text)
        category, problem = parse_category(raw)
        if category is None:
            # 확신도 0 → 부모 클래스가 기본 카테고리로 보냅니다.
            return self.default_category, 0.0, f"분류기 출력 해석 실패({problem}): {raw!r}"
        return category, 1.0, f"분류기({self.classifier.name}) 출력: {raw.strip()!r}"

    def describe(self) -> dict[str, str]:
        # 평가 보고서의 "실행 환경" 표에 들어갑니다. 분류기 설정이 바뀌면 결과도 달라지므로 기록해 둡니다.
        return {
            "classifier_model": self.classifier.name,
            "classifier_temperature": str(self.classifier.temperature),
            "classifier_extra_body": str(self.classifier.extra_body),
        }

    def warmup(self) -> None:
        """모델을 메모리에 미리 올립니다.

        첫 호출에는 모델을 디스크에서 메모리로 올리는 시간(수 초)이 섞여서,
        평가할 때 평균 지연이 실제보다 훨씬 커 보입니다. 측정 전에 한 번 불러 두면
        "모델이 올라가 있을 때의 속도"를 잴 수 있습니다. (콜드 스타트는 별도로 재세요)
        """
        self._ask("hello")
