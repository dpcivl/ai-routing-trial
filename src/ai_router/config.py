"""configs/models.yaml 을 읽어서 파이썬 객체로 바꿔주는 모듈.

YAML 파일을 그냥 dict로 읽으면 오타가 있어도 실제로 그 값을 쓸 때까지 모릅니다.
pydantic 모델로 한 번 검증하면 프로그램 시작 시점에 바로 에러를 알 수 있습니다.
(임베디드의 부팅 시 설정값 검증과 같은 역할)
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from ai_router.types import Category

# 이 파일 위치(src/ai_router/config.py) 기준으로 프로젝트 루트를 계산합니다.
# parents[0]=ai_router, [1]=src, [2]=프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "models.yaml"


class BackendConfig(BaseModel):
    base_url: str
    api_key: str = "ollama"
    timeout_sec: float = 300


class ModelConfig(BaseModel):
    name: str
    temperature: float = 0.7
    max_tokens: int = 2048
    # 요청 본문에 그대로 덧붙일 추가 필드 (엔진마다 다른 옵션용. 예: {"reasoning_effort": "none"}).
    # 엔진 전용 옵션은 코드가 아니라 설정 파일에 두어야 Ollama ↔ vLLM 전환 때 코드를 안 고칩니다.
    extra_body: dict[str, Any] = Field(default_factory=dict)


class AppConfig(BaseModel):
    backend: BackendConfig
    default_category: Category
    # LLM 분류기 라우터용 모델. `--router llm`을 쓰지 않으면 없어도 됩니다.
    router_llm: ModelConfig | None = None
    # dict의 키가 Category로 검증되므로 "codng" 같은 오타는 로딩 시점에 에러가 납니다.
    models: dict[Category, ModelConfig]

    def model_for(self, category: Category) -> ModelConfig:
        return self.models[category]


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    config = AppConfig.model_validate(raw)

    # 세 카테고리 모두 모델이 지정되어 있는지 확인합니다.
    missing = [c for c in Category if c not in config.models]
    if missing:
        raise ValueError(f"{path}에 다음 카테고리의 모델 설정이 없습니다: {missing}")
    return config
