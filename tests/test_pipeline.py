"""파이프라인 테스트: 가짜(Fake) 백엔드를 써서 Ollama 없이 동작을 확인합니다.

임베디드에서 실제 하드웨어 대신 목(mock) 드라이버를 붙여 로직만 테스트하는 것과 같습니다.
"""

from pathlib import Path

from fakes import FakeBackend

from ai_router.config import load_config
from ai_router.pipeline import RoutingPipeline
from ai_router.routers import RuleBasedRouter
from ai_router.types import UserRequest


def make_pipeline():
    config = load_config()
    backend = FakeBackend()
    return RoutingPipeline(RuleBasedRouter(), backend, config), backend, config


def test_routes_to_configured_coding_model():
    pipeline, backend, config = make_pipeline()
    result = pipeline.run(UserRequest(text="파이썬 함수 구현해줘"))
    assert [c["model"] for c in backend.calls] == [config.models["coding"].name]
    assert result.chat.tokens_per_sec == 200.0  # 20토큰 / 0.1초


def test_image_request_uses_vision_model():
    pipeline, backend, config = make_pipeline()
    pipeline.run(UserRequest(text="이거 뭐야?", image_paths=[Path("x.png")]))
    assert [c["model"] for c in backend.calls] == [config.models["vision"].name]


def test_dry_run_does_not_call_backend():
    pipeline, backend, _ = make_pipeline()
    result = pipeline.run(UserRequest(text="파이썬 함수 구현해줘"), dry_run=True)
    assert backend.calls == []
    assert result.chat is None
