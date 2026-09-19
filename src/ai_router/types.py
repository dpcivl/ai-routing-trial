"""프로젝트 전체에서 공유하는 데이터 타입 정의.

임베디드로 비유하면 여러 모듈이 함께 include 하는 공용 헤더(types.h)입니다.
여기 있는 클래스들은 "데이터를 담는 그릇"일 뿐 동작(로직)은 거의 없습니다.

pydantic의 BaseModel을 쓰면 C의 struct처럼 필드를 선언할 수 있고,
잘못된 타입의 값이 들어오면 즉시 에러를 내줍니다(런타임 타입 검사).
"""

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class Category(StrEnum):
    """라우팅 목적지(카테고리).

    StrEnum은 enum이면서 동시에 문자열처럼 쓸 수 있습니다.
    예: Category.CODING == "coding" → True
    그래서 YAML 설정이나 JSON 결과 파일에 그대로 저장하기 편합니다.
    """

    REASONING = "reasoning"  # 일반 질문, 분석, 설명, 추론
    CODING = "coding"  # 코드 작성, 디버깅, 리팩터링
    # 디자인 담당. 이미지 분석(UI 스크린샷, 시안)과 텍스트로 된 UI/UX 디자인 질문을 처리합니다.
    VISION = "vision"


class UserRequest(BaseModel):
    """사용자가 보낸 요청 하나."""

    text: str
    # 첨부 이미지 경로 목록. 비어 있으면 텍스트만 있는 요청입니다.
    image_paths: list[Path] = Field(default_factory=list)

    @property
    def has_images(self) -> bool:
        return len(self.image_paths) > 0


class RouteDecision(BaseModel):
    """라우터가 내린 판단 결과.

    카테고리만 반환하지 않고 "왜 그렇게 판단했는지"와 "얼마나 확신하는지"를 함께 남깁니다.
    나중에 라우팅 결과 문서를 쓸 때 오답 원인을 분석하는 데 꼭 필요한 정보입니다.
    """

    category: Category
    router_name: str  # 어떤 라우터가 판단했는지 (예: "rule")
    confidence: float = Field(ge=0.0, le=1.0)  # 0.0 ~ 1.0 사이 확신도
    reason: str  # 사람이 읽을 수 있는 판단 근거
    latency_ms: float = 0.0  # 라우팅에 걸린 시간(밀리초)
    is_fallback: bool = False  # 확신이 낮아 기본 카테고리로 보냈는지 여부


class ChatResult(BaseModel):
    """모델 호출 결과와 성능 측정값."""

    model: str
    text: str
    ttft_ms: float | None = None  # Time To First Token: 첫 글자가 나올 때까지 걸린 시간
    total_ms: float  # 요청 시작부터 응답 완료까지 걸린 전체 시간
    completion_tokens: int | None = None  # 모델이 생성한 토큰 수

    @property
    def tokens_per_sec(self) -> float | None:
        """초당 생성 토큰 수 (생성 속도).

        첫 토큰 이후 구간만으로 계산합니다. 첫 토큰 전에는 모델 로딩과
        프롬프트 처리 시간이 섞여 있어서 "순수 생성 속도"가 아니기 때문입니다.
        """
        if self.completion_tokens is None or self.ttft_ms is None:
            return None
        gen_ms = self.total_ms - self.ttft_ms
        if gen_ms <= 0:
            return None
        return self.completion_tokens / (gen_ms / 1000)


class PipelineResult(BaseModel):
    """요청 하나를 처리한 전체 결과 (라우팅 판단 + 모델 응답)."""

    request: UserRequest
    decision: RouteDecision
    chat: ChatResult | None = None  # dry-run(라우팅만 확인)일 때는 None
