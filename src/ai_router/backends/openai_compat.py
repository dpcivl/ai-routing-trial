"""OpenAI 호환 API를 쓰는 백엔드 (Ollama, vLLM 공용).

왜 Ollama 전용 라이브러리 대신 OpenAI SDK를 쓰나요?
  - Ollama는 http://localhost:11434/v1 에서 OpenAI와 같은 형식의 API를 제공합니다.
  - vLLM도 같은 형식을 제공합니다.
  - 따라서 이 클래스 하나로 지금은 Ollama, 회사에서는 vLLM을 부를 수 있습니다.
    (configs/models.yaml 의 base_url만 바꾸면 됩니다)

응답은 스트리밍(stream=True)으로 받습니다. 한 번에 받으면 "첫 토큰까지 걸린 시간(TTFT)"을
잴 수 없기 때문입니다. 스트리밍은 UART로 바이트가 하나씩 들어오는 것처럼
모델이 토큰을 만들 때마다 조각(chunk)으로 보내주는 방식입니다.
"""

import base64
import mimetypes
import time
from pathlib import Path

from openai import OpenAI

from ai_router.backends.base import ChatBackend
from ai_router.config import BackendConfig
from ai_router.types import ChatResult


def _image_to_data_url(path: Path) -> str:
    """이미지 파일을 base64 문자열로 인코딩한 data URL로 바꿉니다.

    API는 JSON(텍스트)으로 통신하므로 바이너리 이미지를 그대로 보낼 수 없습니다.
    그래서 base64로 텍스트화해서 "data:image/png;base64,iVBOR..." 형태로 보냅니다.
    """
    mime, _ = mimetypes.guess_type(path.name)
    if mime is None or not mime.startswith("image/"):
        raise ValueError(f"이미지 파일이 아닌 것 같습니다: {path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


class OpenAICompatBackend(ChatBackend):
    def __init__(self, config: BackendConfig):
        self._client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout_sec,
        )

    def chat(
        self,
        model: str,
        prompt: str,
        image_paths: list[Path] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> ChatResult:
        # --- 1. 메시지 구성 -------------------------------------------------
        # 이미지가 없으면 content는 단순 문자열입니다.
        # 이미지가 있으면 content는 [텍스트 조각, 이미지 조각, ...] 리스트가 됩니다.
        if image_paths:
            content: str | list[dict] = [{"type": "text", "text": prompt}]
            for p in image_paths:
                content.append({"type": "image_url", "image_url": {"url": _image_to_data_url(p)}})
        else:
            content = prompt
        messages = [{"role": "user", "content": content}]

        # --- 2. 스트리밍 요청 + 시간 측정 -----------------------------------
        # perf_counter는 시스템 시계 변경의 영향을 받지 않는 고해상도 타이머입니다.
        # (임베디드의 free-running 하드웨어 타이머와 비슷)
        start = time.perf_counter()
        ttft_ms: float | None = None
        pieces: list[str] = []
        completion_tokens: int | None = None

        stream = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            # 스트림 마지막에 토큰 사용량(usage)을 함께 보내달라는 옵션
            stream_options={"include_usage": True},
        )
        for chunk in stream:
            # 마지막 chunk에는 choices가 비어 있고 usage만 들어 있습니다.
            if chunk.usage is not None:
                completion_tokens = chunk.usage.completion_tokens
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                if ttft_ms is None:
                    ttft_ms = (time.perf_counter() - start) * 1000
                pieces.append(delta)

        total_ms = (time.perf_counter() - start) * 1000
        return ChatResult(
            model=model,
            text="".join(pieces),
            ttft_ms=ttft_ms,
            total_ms=total_ms,
            completion_tokens=completion_tokens,
        )

    def list_models(self) -> list[str]:
        return [m.id for m in self._client.models.list()]
