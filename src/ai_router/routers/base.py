"""모든 라우터의 공통 부모 클래스.

"템플릿 메서드 패턴"을 씁니다.
  - route()   : 공통 처리 순서를 정의 (부모가 구현, 하위 클래스는 건드리지 않음)
  - _classify(): 실제 판단 로직 (하위 클래스가 각자 구현)

route() 의 처리 순서:
  1. 이미지가 첨부되어 있으면 → 무조건 VISION
     이미지를 "볼 수 있는" 모델은 vision 모델뿐이므로 이것은 선택이 아니라 제약 조건입니다.
     (UART 데이터를 SPI 드라이버로 보낼 수 없는 것과 같습니다)
  2. 텍스트만 있으면 → 하위 클래스의 _classify() 로 판단
  3. 확신도가 기준치(threshold)보다 낮으면 → 기본 카테고리로 보냄 (fallback)
  4. 전체 걸린 시간을 기록

이렇게 해두면 규칙/임베딩/LLM 라우터를 새로 만들 때 2번만 구현하면 되고,
세 라우터가 같은 조건에서 비교됩니다.
"""

import time
from abc import ABC, abstractmethod

from ai_router.backends.base import ChatBackend
from ai_router.config import AppConfig
from ai_router.types import Category, RouteDecision, UserRequest


class Router(ABC):
    # 하위 클래스에서 덮어씁니다. 결과 파일과 문서에 이 이름이 기록됩니다.
    name: str = "base"

    def __init__(
        self,
        default_category: Category = Category.REASONING,
        confidence_threshold: float = 0.5,
    ):
        self.default_category = default_category
        self.confidence_threshold = confidence_threshold

    @classmethod
    def from_config(cls, config: AppConfig, backend: ChatBackend, confidence_threshold: float) -> "Router":
        """설정에서 라우터를 만드는 공장(factory) 메서드.

        기본 구현은 백엔드가 필요 없는 라우터용입니다. 모델을 호출해야 하는 라우터(llm)는
        이 메서드를 덮어써서 backend와 모델 설정을 받아 갑니다. 덕분에 CLI는 라우터 종류를
        몰라도 `ROUTERS[name].from_config(...)` 한 줄로 만들 수 있습니다.
        """
        return cls(default_category=config.default_category, confidence_threshold=confidence_threshold)

    def describe(self) -> dict[str, str]:
        """결과 재현에 필요한 라우터 고유 설정 (보고서에 기록됨). 기본은 없음."""
        return {}

    def warmup(self) -> None:
        """평가를 시작하기 전에 필요한 준비(예: 모델 로딩). 기본은 할 일 없음."""
        return None  # 일부러 비워 둔 기본 구현 (하위 클래스가 필요하면 덮어씀)

    @abstractmethod
    def _classify(self, text: str) -> tuple[Category, float, str]:
        """텍스트를 보고 (카테고리, 확신도 0~1, 판단 근거)를 돌려줍니다."""

    def route(self, request: UserRequest) -> RouteDecision:
        start = time.perf_counter()

        if request.has_images:
            category, confidence, reason = (
                Category.VISION,
                1.0,
                f"이미지 {len(request.image_paths)}개 첨부 → vision 모델만 처리 가능",
            )
            is_fallback = False
        else:
            category, confidence, reason = self._classify(request.text)
            is_fallback = confidence < self.confidence_threshold
            if is_fallback:
                reason = (
                    f"확신도 {confidence:.2f} < 기준 {self.confidence_threshold:.2f} "
                    f"→ 기본값({self.default_category}) 사용. 원래 판단: {category} ({reason})"
                )
                category = self.default_category

        latency_ms = (time.perf_counter() - start) * 1000
        return RouteDecision(
            category=category,
            router_name=self.name,
            confidence=confidence,
            reason=reason,
            latency_ms=latency_ms,
            is_fallback=is_fallback,
        )
