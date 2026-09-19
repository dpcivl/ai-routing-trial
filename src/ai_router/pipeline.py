"""요청 처리 파이프라인: 입력 → 라우팅 → 모델 호출 → 결과.

임베디드로 비유하면 인터럽트 디스패처입니다.
  - 라우터 = "어느 핸들러(ISR)로 보낼지" 결정하는 부분
  - 백엔드 = 실제로 일을 처리하는 핸들러
  - 파이프라인 = 둘을 연결하는 main loop
"""

from ai_router.backends.base import ChatBackend
from ai_router.config import AppConfig
from ai_router.routers.base import Router
from ai_router.types import PipelineResult, UserRequest


class RoutingPipeline:
    def __init__(self, router: Router, backend: ChatBackend, config: AppConfig):
        self.router = router
        self.backend = backend
        self.config = config

    def run(self, request: UserRequest, dry_run: bool = False) -> PipelineResult:
        """요청 하나를 처리합니다.

        dry_run=True 이면 라우팅 판단만 하고 모델은 호출하지 않습니다.
        Ollama가 없어도 라우터를 테스트할 수 있게 하기 위한 옵션입니다.
        """
        decision = self.router.route(request)
        if dry_run:
            return PipelineResult(request=request, decision=decision)

        model_cfg = self.config.model_for(decision.category)
        chat = self.backend.chat(
            model=model_cfg.name,
            prompt=request.text,
            image_paths=request.image_paths,
            temperature=model_cfg.temperature,
            max_tokens=model_cfg.max_tokens,
        )
        return PipelineResult(request=request, decision=decision, chat=chat)
