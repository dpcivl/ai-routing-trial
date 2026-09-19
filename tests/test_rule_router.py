"""규칙 기반 라우터 단위 테스트.

pytest는 test_로 시작하는 함수를 자동으로 찾아 실행합니다.
assert 뒤의 조건이 거짓이면 테스트 실패입니다. (임베디드의 assert 매크로와 같음)
실행: uv run pytest
"""

from pathlib import Path

from ai_router.routers import RuleBasedRouter
from ai_router.types import Category, UserRequest


def route(text: str, images: list[str] | None = None):
    router = RuleBasedRouter()
    return router.route(UserRequest(text=text, image_paths=[Path(p) for p in images or []]))


def test_coding_keywords():
    assert route("파이썬으로 퀵정렬 함수를 구현해줘").category == Category.CODING


def test_code_block_is_strong_signal():
    d = route("이거 봐줘\n```c\nint main() { return 0; }\n```")
    assert d.category == Category.CODING
    assert d.confidence >= 0.8


def test_design_question_goes_to_vision():
    assert route("로그인 페이지 레이아웃을 어떻게 배치하면 좋을까?").category == Category.VISION


def test_reasoning_keywords():
    assert route("전세와 월세의 장단점을 비교해줘").category == Category.REASONING


def test_image_forces_vision_even_for_code_question():
    # 코드 키워드가 있어도 이미지가 있으면 vision 모델만 처리할 수 있습니다.
    d = route("이 코드 에러 화면 보고 버그 찾아줘", images=["error.png"])
    assert d.category == Category.VISION
    assert d.confidence == 1.0


def test_no_keywords_falls_back_to_default():
    d = route("오늘 저녁 메뉴 추천해줘")
    assert d.is_fallback
    assert d.category == Category.REASONING


def test_korean_particles_are_matched():
    # "함수를"처럼 조사가 붙어도 '함수'로 인식되어야 합니다.
    assert route("이 함수를 고쳐줘").category == Category.CODING


def test_same_word_is_not_double_counted():
    # 'UI'가 한국어/영어 목록에 중복으로 있으면 점수가 두 번 더해지는 버그가 있었습니다.
    d = route("UI 개선")
    assert d.reason.count("ui") + d.reason.count("UI") == 1
