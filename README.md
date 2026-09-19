# ai-routing-trial

로컬 소형 LLM 여러 개를 두고, 사용자 프롬프트를 보고 **알맞은 모델로 자동 연결(라우팅)**하는 학습용 프로젝트입니다.
MacBook Pro M1 (RAM 16GB)과 [Ollama](https://ollama.com)에서 동작합니다.

| 카테고리 | 담당 | 기본 모델 |
|---|---|---|
| `reasoning` | 일반 질문, 설명, 분석, 추론 | `deepseek-r1:8b` |
| `coding` | 코드 작성, 디버깅, 리팩터링 | `qwen2.5-coder:7b` |
| `vision` | 이미지 분석, UI/UX 디자인 질문 | `ministral-3:8b` |

모델은 [configs/models.yaml](configs/models.yaml)에서 바꿀 수 있습니다.

## 빠른 시작

```bash
# 1. 의존성 설치 (uv 필요: brew install uv)
uv sync

# 2. 라우팅 판단만 확인 (Ollama 없이 동작)
uv run ai-router ask "파이썬으로 퀵정렬 구현해줘" --dry-run

# 3. 라우터 정확도 평가 + 보고서 생성 (Ollama 없이 동작)
uv run ai-router eval-routing

# 4. 실제 모델 호출 (Ollama 설치 필요 → docs/setup.md)
uv run ai-router check
uv run ai-router ask "RTOS와 베어메탈의 차이를 설명해줘"
uv run ai-router ask "이 화면에서 개선할 점은?" --image screenshot.png
```

## 폴더 구조

```
configs/models.yaml      카테고리별 모델 설정
src/ai_router/
  types.py               공용 데이터 타입
  config.py              설정 로드·검증
  backends/              모델 호출 (OpenAI 호환 API → Ollama, vLLM 공용)
  routers/               라우터 구현 (rule, 이후 embedding, llm)
  pipeline.py            라우팅 → 모델 호출 연결
  evaluation.py          라우팅 정확도 평가 + Markdown 보고서 생성
  cli.py                 ai-router 명령
data/eval/               정답이 달린 평가용 프롬프트 (JSONL)
results/                 평가 원시 결과 (JSON)
docs/
  setup.md               환경 구축
  architecture.md        구조와 설계 결정
  routing/               라우팅 평가 보고서 (자동 생성)
  templates/             벤치마크 / 모델 비교 / 라우팅 분석 문서 템플릿
tests/                   단위 테스트
```

## 진행 현황

- [x] 프로젝트 뼈대, OpenAI 호환 백엔드
- [x] ① 규칙 기반 라우터 + 평가셋 v1 (45문항) + 자동 보고서
- [ ] Ollama 실제 연결 확인, 첫 속도 벤치마크
- [ ] ② 임베딩 유사도 라우터
- [ ] ③ 소형 LLM 분류기 라우터
- [ ] 라우터 3종 비교 보고서
- [ ] 오픈소스 라우터(semantic-router, RouteLLM 등) 비교
- [ ] 평가셋 확장 (실제 사용 프롬프트 수집)

## 문서

- [환경 구축](docs/setup.md)
- [구조와 설계 결정](docs/architecture.md)
- [라우팅 평가 보고서](docs/routing/)
- [모델 후보 조사와 순위 (2026-09)](docs/comparisons/2026-09-model-selection.md)
