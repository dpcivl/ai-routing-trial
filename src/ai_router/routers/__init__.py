"""라우터 모음.

ROUTERS 딕셔너리에 이름 → 클래스를 등록해 두면 CLI에서 --router rule 처럼 이름으로 고를 수 있습니다.
임베딩 라우터, LLM 분류기 라우터를 만들면 여기에 한 줄씩 추가합니다.
"""

from ai_router.routers.base import Router
from ai_router.routers.rule_based import RuleBasedRouter

ROUTERS: dict[str, type[Router]] = {
    RuleBasedRouter.name: RuleBasedRouter,
    # "embedding": EmbeddingRouter,   # 다음 단계에서 추가
    # "llm": LLMClassifierRouter,     # 다음 단계에서 추가
}

__all__ = ["ROUTERS", "Router", "RuleBasedRouter"]
