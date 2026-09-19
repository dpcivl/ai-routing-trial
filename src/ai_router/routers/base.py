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
