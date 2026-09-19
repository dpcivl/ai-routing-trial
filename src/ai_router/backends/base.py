"""모델 백엔드의 공통 인터페이스.

임베디드의 HAL(Hardware Abstraction Layer)과 같은 개념입니다.
  - 라우터와 파이프라인은 이 인터페이스(ChatBackend)만 알고 있습니다.
  - 실제로 Ollama를 부르든 vLLM을 부르든 상위 코드는 바뀌지 않습니다.

ABC(Abstract Base Class)는 C++의 순수 가상 함수가 있는 클래스와 비슷합니다.
@abstractmethod가 붙은 메서드를 구현하지 않은 하위 클래스는 객체를 만들 수 없습니다.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ai_router.types import ChatResult


class ChatBackend(ABC):
    @abstractmethod
    def chat(
        self,
        model: str,
        prompt: str,
        image_paths: list[Path] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system: str | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> ChatResult:
        """모델에 프롬프트(와 이미지)를 보내고 응답과 측정값을 돌려줍니다.

        system: 모델의 역할/규칙을 알려주는 시스템 메시지 (없으면 생략)
        extra_body: 엔진 전용 추가 옵션 (요청 본문에 그대로 합쳐짐)
        """

    @abstractmethod
    def list_models(self) -> list[str]:
        """서버에 준비된(다운로드된) 모델 이름 목록을 돌려줍니다."""
