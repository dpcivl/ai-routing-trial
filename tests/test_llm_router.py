"""소형 LLM 분류기 라우터 테스트. FakeBackend가 "모델의 답"을 대신 말해 줍니다.

실제 모델의 분류 정확도는 여기서 알 수 없습니다. 이 테스트는
"모델이 이렇게 답하면 라우터가 올바르게 해석하는가"(파싱, fallback, 인자 전달)만 확인합니다.
"""

from pathlib import Path

import pytest
from fakes import FakeBackend

from ai_router.config import ModelConfig, load_config
from ai_router.evaluation import EvalItem, run_eval
from ai_router.routers import ROUTERS, LLMClassifierRouter
from ai_router.routers.llm_classifier import parse_category
from ai_router.types import Category, UserRequest


def make_router(replies: list[str]):
    backend = FakeBackend(replies)
    classifier = ModelConfig(name="fake-classifier", temperature=0.0, max_tokens=32, extra_body={"x": 1})
    return LLMClassifierRouter(backend=backend, classifier=classifier), backend


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("coding", Category.CODING),
        ("Coding.", Category.CODING),
        ("  **vision**\n", Category.VISION),
        ("Answer: reasoning", Category.REASONING),
        # 생각 과정 안의 단어는 무시하고 마지막 답만 봐야 합니다.
        ("<think>this might be coding or vision...</think>reasoning", Category.REASONING),
    ],
)
def test_parse_success(raw, expected):
    assert parse_category(raw) == (expected, "")


@pytest.mark.parametrize(
    "raw",
    [
        "",  # 빈 응답
        "   \n",
        "<think>still thinking about coding</think>",  # 생각만 하고 답이 없음
        "I am not sure",  # 카테고리 단어 없음
        "coding or reasoning",  # 두 종류가 섞임
        "encoding",  # 단어의 일부일 뿐 (\b 경계)
    ],
)
def test_parse_failure(raw):
    category, problem = parse_category(raw)
    assert category is None
    assert problem


def test_routes_to_model_answer():
    router, _ = make_router(["coding"])
    d = router.route(UserRequest(text="git 커밋 메시지 수정법"))
    assert d.category == Category.CODING
    assert d.confidence == 1.0
    assert not d.is_fallback
    assert d.router_name == "llm"


def test_unparseable_answer_falls_back_to_default():
    router, _ = make_router(["잘 모르겠어요"])
    d = router.route(UserRequest(text="아무 말"))
    assert d.is_fallback
    assert d.category == Category.REASONING
    assert "해석 실패" in d.reason


def test_image_request_skips_classifier():
    # 이미지가 있으면 분류기를 호출하지 않아야 합니다 (시간과 메모리 절약).
    router, backend = make_router(["coding"])
    d = router.route(UserRequest(text="이거 뭐야?", image_paths=[Path("x.png")]))
    assert d.category == Category.VISION
    assert backend.calls == []


def test_classifier_receives_settings_and_wrapped_prompt():
    router, backend = make_router(["vision"])
    router.route(UserRequest(text="버튼 색 추천"))
    call = backend.calls[0]
    assert call["model"] == "fake-classifier"
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 32
    assert call["extra_body"] == {"x": 1}
    assert "버튼 색 추천" in call["prompt"]
    assert "reasoning, coding, vision" in call["system"]


def test_long_input_is_truncated():
    router, backend = make_router(["reasoning"])
    router.route(UserRequest(text="가" * 10000))
    assert len(backend.calls[0]["prompt"]) < 2200


def test_warmup_runs_once_before_eval_and_is_not_counted():
    router, backend = make_router(["reasoning", "coding"])  # 첫 답은 warmup이 소비
    items = [EvalItem(id="t1", text="함수 짜줘", expected=Category.CODING)]
    records = run_eval(router, items)
    assert len(backend.calls) == 2  # warmup 1 + 문항 1
    assert len(records) == 1
    assert records[0].decision.category == Category.CODING


def test_from_config_uses_router_llm_section():
    config = load_config()
    router = ROUTERS["llm"].from_config(config, FakeBackend(), 0.5)
    assert router.classifier.name == config.router_llm.name
    assert router.describe()["classifier_model"] == config.router_llm.name


def test_from_config_without_router_llm_raises():
    config = load_config().model_copy(update={"router_llm": None})
    with pytest.raises(ValueError, match="router_llm"):
        ROUTERS["llm"].from_config(config, FakeBackend(), 0.5)


def test_default_config_disables_thinking_for_classifier():
    # 생각 모드가 켜져 있으면 max_tokens=32를 생각에 다 써서 빈 응답이 나옵니다.
    assert load_config().router_llm.extra_body.get("reasoning_effort") == "none"
