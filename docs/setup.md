# 환경 구축 가이드 (macOS, Apple Silicon)

## 1. Ollama 설치

```bash
brew install ollama
```

또는 https://ollama.com/download 에서 macOS 앱을 받아도 됩니다. 앱으로 설치하면 메뉴 막대에서 자동 실행됩니다.

Homebrew로 설치했다면 서버를 직접 실행합니다 (터미널 창 하나를 계속 띄워 둠):

```bash
ollama serve
```

## 2. 모델 다운로드

`configs/models.yaml`에 적힌 모델을 받습니다. 합계 약 28GB입니다 (5.2 + 15 + 7.6). 디스크 여유 공간을 확인하세요. 코딩 모델(devstral-small-2)은 Ollama 0.13.3 이상이 필요합니다.

```bash
ollama pull deepseek-r1:8b
ollama pull devstral-small-2
ollama pull gemma4:12b
```

받은 뒤 연결 상태를 확인합니다.

```bash
uv run ai-router check
```

## 3. 16GB 메모리에서의 주의점

- Ollama는 기본적으로 메모리가 허락하는 만큼 여러 모델을 동시에 올려둡니다. 메모리가 부족하면 macOS가 스왑(디스크)을 쓰기 시작하고 속도가 크게 떨어집니다.
- 한 번에 모델 하나만 올리게 하려면 Ollama 서버를 이렇게 실행합니다.

```bash
OLLAMA_MAX_LOADED_MODELS=1 ollama serve
```

- 이렇게 하면 카테고리가 바뀔 때마다 모델을 교체(언로드 → 로드)합니다. 교체 시간은 첫 요청의 TTFT에 포함되어 측정됩니다.
- 현재 메모리에 올라간 모델은 `ollama ps`로 확인합니다.
- 벤치마크를 돌릴 때는 브라우저 같은 무거운 앱을 닫아야 측정값이 안정적입니다.

## 4. 알아둘 점: "생각하는(thinking)" 모델

`deepseek-r1`은 답하기 전에 내부 추론 과정(thinking)을 먼저 생성할 수 있습니다.
- 이 과정은 보통 응답 본문(`content`)과 별도 필드로 전달됩니다. 이 경우 현재 코드의 TTFT는 **"생각이 끝나고 첫 답변 글자가 나온 시점"**을 측정합니다. (Ollama 버전에 따라 동작이 다를 수 있으니 첫 실행 때 확인이 필요합니다.)
- 추론 품질은 좋아지지만 체감 속도는 느려집니다. thinking 켜기/끄기 비교는 좋은 벤치마크 주제입니다.

## 5. 개발 명령어 모음

```bash
uv sync                              # 의존성 설치 (처음 한 번, pyproject.toml 변경 시)
uv run pytest                        # 테스트
uv run ruff check src tests          # 코드 검사
uv run ruff format src tests         # 코드 자동 정렬
uv run ai-router eval-routing        # 라우팅 평가 + 보고서 생성
```
