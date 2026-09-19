"""테스트용 가짜 백엔드. 실제 서버 없이 "모델이 이렇게 답했다"를 흉내 냅니다.

임베디드에서 센서 대신 정해진 값을 돌려주는 목(mock) 드라이버를 붙여 로직만 시험하는 것과 같습니다.
"""

from ai_router.backends.base import ChatBackend
from ai_router.types import ChatResult


class FakeBackend(ChatBackend):
    def __init__(self, replies: list[str] | None = None):
        self.replies = list(replies or [])  # 호출할 때마다 앞에서부터 하나씩 꺼내 답함
        self.calls: list[dict] = []  # 어떤 인자로 호출됐는지 기록

    def chat(
        self,
        model,
        prompt,
        image_paths=None,
        temperature=0.7,
        max_tokens=2048,
        system=None,
        extra_body=None,
    ):
        self.calls.append(
            {
                "model": model,
                "prompt": prompt,
                "system": system,
                "extra_body": extra_body,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        text = self.replies.pop(0) if self.replies else f"[{model}] 응답"
        return ChatResult(model=model, text=text, ttft_ms=10, total_ms=110, completion_tokens=20)

    def list_models(self):
        return []
