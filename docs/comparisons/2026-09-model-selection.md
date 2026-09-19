# [모델 비교] M1 16GB 기준 추론·코딩·비전 모델 후보 조사와 순위

- 작성일: 2026-09-19
- 조사 방식: **전용 조사 스킬은 사용하지 못했습니다.** 계정의 스킬 목록(`ListSkills`)과 검색(`SearchSkills`)에서 조사용 스킬을 찾지 못해, Claude Code의 웹 도구 `WebSearch`(검색)와 `WebFetch`(페이지 읽기)로 직접 조사했습니다. 신뢰도 순서는 모델 공식 카드 → 종합 벤치마크 사이트 → 2차 블로그입니다.
- 성격: **논문·모델 카드에 공개된 수치를 모은 조사 문서**입니다. 이 맥북에서 직접 돌려서 잰 값이 아닙니다.
- 후속 작업: 이 문서의 상위 후보를 우리 평가셋으로 직접 측정 (→ 7장)

---

## 0. 먼저 읽어 주세요 (이 문서의 한계)

1. **"Haiku 5"는 아직 존재하지 않습니다.** 조사 시점(2026-09)에 가장 작은 Claude는 **Haiku 4.5**입니다. 그래서 기준(anchor)은 **Sonnet 5**와 **Haiku 4.5**로 잡았습니다.
2. **Sonnet 5 점수는 출처끼리 서로 어긋납니다.** Anthropic 발표 페이지는 점수표가 이미지라서 글자로 읽을 수 없었고, 2차 출처마다 인용하는 벤치마크 종류와 버전이 다릅니다. 예를 들어 어떤 곳은 SWE-bench Verified 72.7%(Haiku 4.5의 73.3%보다 낮음)를, 다른 곳은 SWE-Bench Pro 63.2를 Anthropic 수치라고 소개합니다. **Sonnet 5 수치는 "참고용"으로만 봐주세요.**
3. **벤치마크 종류와 버전이 표마다 다릅니다.** 같은 이름(예: LiveCodeBench)이라도 버전과 측정 기간이 다르면 직접 비교할 수 없습니다. 아래 표에서는 비교 가능한 것끼리만 순위를 매기고, 그렇지 않은 것은 "비교 불가"로 표시했습니다.
4. **대부분의 소형 모델 점수는 제작사가 직접 발표한 값이고, 생각(thinking) 모드를 켠 상태입니다.** 답이 나오기까지 시간이 훨씬 오래 걸립니다. 이 맥북에서의 체감 속도와는 별개의 문제입니다.
5. **"디자인 질문에 답하는 능력"을 재는 공개 벤치마크는 찾지 못했습니다.** 아래 비전 순위는 이미지 이해 능력(MMMU 계열)만 반영합니다.

---

## 1. 후보를 추린 기준: 메모리

- 이 맥북(16GB)은 CPU와 GPU가 메모리를 나눠 씁니다. GPU가 쓸 수 있는 몫은 보통 전체의 약 2/3(≈10GB, 저의 추정치)입니다.
- 모델은 **한 번에 하나만 올리는 것**(`OLLAMA_MAX_LOADED_MODELS=1`)을 전제로 했고, **파일 크기 약 10GB 이하**만 "적합"으로 봤습니다. 컨텍스트(KV 캐시)에도 메모리가 필요해서 여유를 남긴 기준입니다.

| 모델 (Ollama 태그) | 파일 크기 | 판정 | 비고 |
|---|---|---|---|
| `qwen3.5:9b` | 6.6GB | ✅ | 텍스트+이미지 |
| `gemma4:12b` | 7.6GB | ✅ | 텍스트+이미지, 컨텍스트 256K |
| `gemma4:e4b` (qat) | 6.1GB | ✅ | 기본 태그(q4_K_M)는 9.6GB |
| `ministral-3:3b / 8b / 14b` | 3.0 / 6.0 / 9.1GB | ✅ | 텍스트+이미지 |
| `deepseek-r1:8b` | 5.2GB | ✅ | 실제 모델은 DeepSeek-R1-0528-Qwen3-8B |
| `deepseek-r1:14b` | 9.0GB | ⚠️ 빠듯 | 실제 모델은 R1-Distill-Qwen-14B (구형) |
| `qwen2.5-coder:7b / 14b` | 4.7 / 9.0GB | ✅ / ⚠️ | 텍스트 전용 |
| `deepseek-coder-v2:16b` (lite, q4_0) | 8.9GB | ⚠️ 빠듯 | 컨텍스트 4K(instruct q4_0만 160K) |
| `minicpm-v4.5:8b` | 6.1GB | ✅ | 텍스트+이미지, 컨텍스트 40K |
| `gpt-oss:20b` | 14GB | ❌ | 로컬 메모리 초과 |
| `devstral-small-2:24b` | 15GB | ❌ | 로컬 메모리 초과 |

---

## 2. 기준선 (Claude)

| 벤치마크 | Sonnet 5 | Haiku 4.5 | 신뢰도 |
|---|---|---|---|
| GPQA Diamond (과학 추론) | 78.0 | 72.2 | Sonnet 5: 2차 출처, 재검증 안 됨 / Haiku 4.5: BenchLM |
| MMLU-Pro (지식) | 확인 못함 | 78.7 | BenchLM |
| MMMU (이미지 이해) | 76.3 | 확인 못함 | 2차 출처, 재검증 안 됨 |
| MathVista (이미지 수학) | 76.6 | 확인 못함 | 2차 출처, 재검증 안 됨 |
| SWE-bench Verified (실제 코드 수정) | 72.7 | **73.3** | Haiku 4.5는 Anthropic 공식 페이지에서 확인. Sonnet 5는 2차 출처이며 Haiku보다 낮아서 의심스러움 |
| LiveCodeBench | 확인 못함 | 41.2 | BenchLM, 버전 불명. 아래 로컬 모델 수치와 직접 비교 불가 |
| Artificial Analysis 지능 지수 | 38 (페이지 표기가 모호) | 15 (비추론 모드) | 종합 지수, 버전 v4.3 |

> Artificial Analysis 지수는 에이전트·업무 작업 비중이 커서 소형 모델은 모두 낮게 나오고 서로의 차이가 눌립니다. 크기 감각용으로만 쓰세요.

---

## 3. 추론(reasoning) 순위

**순위 기준:** GPQA Diamond (모델 카드에서 대부분 확인됨). 보조로 MMLU-Pro, AIME를 봤습니다.
`대Sonnet5`는 GPQA 78.0 대비 비율, `대Haiku`는 72.2 대비 비율입니다.

| 순위 | 모델 | 크기 | GPQA | 대Sonnet5 | 대Haiku | 보조 지표 | 메모 |
|---|---|---|---|---|---|---|---|
| 1 | Qwen3.5 9B | 6.6GB | 81.7 | 105% | 113% | MMLU-Pro 82.5, AA지수 14 | 사용자 선호 계열(gpt-oss/deepseek) 밖 |
| 2 | **Gemma 4 12B** | 7.6GB | 78.8 | 101% | 109% | MMLU-Pro 77.2, AIME 2026 77.5, AA지수 14 | 라이선스 Apache 2.0 |
| 3 | Ministral 3 14B | 9.1GB | 71.2* | 91% | 99% | AIME25 85.0 | *아래 주의 |
| 4 | Ministral 3 8B | 6.0GB | 66.8* | 86% | 93% | AIME25 78.7 | *아래 주의 |
| 5 | **DeepSeek-R1-0528-Qwen3-8B** (`deepseek-r1:8b`) | 5.2GB | 61.1 | 78% | 85% | AIME25 76.3, AA지수 8~10 | MIT 라이선스. 현재 설정 |
| 6 | DeepSeek-R1-Distill-Qwen-14B (`deepseek-r1:14b`) | 9.0GB | 59.1 | 76% | 82% | AIME24 69.7 | 8B(0528)보다 낮고 더 큼 |
| (참고) | gpt-oss:20b | **14GB ❌** | 68.8 | 88% | 95% | LiveCodeBench 77.7 | 메모리 초과, 출처: Artificial Analysis |

**\*주의:** Ministral 3의 GPQA 값은 모델 카드에서 **Reasoning 전용 버전** 표에 있는 수치입니다. Ollama의 `ministral-3` 태그는 Instruct 버전으로 보이고 별도 reasoning 태그는 확인하지 못했습니다. 그래서 Ollama로 받는 모델은 이 수치보다 낮을 가능성이 큽니다.

**읽는 법**
- 사용자 선호 계열(gpt-oss, deepseek)만 보면 **로컬에서 돌릴 수 있는 최선은 `deepseek-r1:8b`**입니다. gpt-oss:20b는 점수는 더 높지만(68.8 vs 61.1) 메모리에 안 들어갑니다.
- **`deepseek-r1:14b`를 올릴 이유가 없습니다.** 더 크지만 GPQA(59.1)와 LiveCodeBench(53.1)가 8B(0528판)보다 모두 낮습니다. 14b는 2025년 1월의 구형 증류 모델이고, 8b는 2025년 5월 업데이트 모델이기 때문입니다.
- 선호 계열을 벗어나면 **Gemma 4 12B와 Qwen3.5 9B가 GPQA에서 약 18~20점 앞섭니다.** 이 수치대로라면 Haiku 4.5를 넘는 수준입니다(단 제작사 발표값이며 생각 모드를 켠 상태).

---

## 4. 코딩(coding) 순위

**순위 기준:** LiveCodeBench v6 (모델 카드에서 확인). SWE-bench Verified는 실제 코드 수정 능력을 재지만 소형 모델은 대부분 점수가 없습니다.

| 순위 | 모델 | 크기 | LiveCodeBench | 기타 | 메모 |
|---|---|---|---|---|---|
| 1 | **Gemma 4 12B** | 7.6GB | 72.0 (v6) | | |
| 2 | Qwen3.5 9B | 6.6GB | 65.6 (v6) | | 사용자 선호 계열 밖 |
| 3 | Ministral 3 14B | 9.1GB | 64.6* | | *Reasoning 버전 수치 |
| 4 | Ministral 3 8B | 6.0GB | 61.6* | | *Reasoning 버전 수치 |
| 5 | DeepSeek-R1-0528-Qwen3-8B | 5.2GB | 60.5 (2408-2505) | | 측정 기간이 달라 엄밀한 비교는 아님 |
| 순위 없음 | Qwen2.5-Coder 7B / 14B | 4.7 / 9.0GB | 확인 못함 | HumanEval 88.4 (7B) | 2024년 모델, 생각 모드 없음. HumanEval은 포화된 벤치마크라 위 표와 비교 불가 |
| 순위 없음 | DeepSeek-Coder-V2-Lite 16B | 8.9GB | 확인 못함 | HumanEval 81.1 | 같은 이유로 비교 불가. 한 블로그가 "약 5GB"라고 했지만 Ollama 실제 파일은 8.9GB |
| (참고) | devstral-small-2 24B | **15GB ❌** | 확인 못함 | SWE-bench Verified **65.8** | 대Haiku 4.5 약 90%. 메모리 초과 |
| (참고) | gpt-oss:20b | **14GB ❌** | 77.7 | | Artificial Analysis 측정 |

**읽는 법**
- **선택하신 devstral은 이 표에서 유일하게 "실제 코드 수정(SWE-bench)" 점수가 공식으로 있는 로컬용 후보**입니다(65.8, Haiku 4.5의 73.3과 약 7.5점 차). 다만 15GB라 회사 vLLM 서버에서 시험하는 게 맞습니다.
- **현재 설정의 `qwen2.5-coder:7b`는 이 자료로는 순위를 매길 수 없습니다.** 최신 소형 범용 모델들과 같은 시험지에서 잰 값이 없습니다. 다만 2024년에 나온 생각 모드 없는 모델이라 LiveCodeBench에서는 뒤질 가능성이 높다고 봅니다(추정).
- 대신 **빠르다는 장점**이 있습니다. 위 1~5위 모델은 생각 과정을 거치므로, 이 맥북에서 코딩 요청에 걸리는 시간이 훨씬 길 수 있습니다. 속도 대 품질은 **직접 재봐야 답이 나옵니다.**

---

## 5. 비전(vision) 순위

**순위 기준:** MMMU-Pro(이미지가 포함된 대학 수준 문제). 다만 모델마다 공개한 벤치마크가 달라서 **점수가 있는 모델만 순위를 매겼습니다.**

| 순위 | 모델 | 크기 | MMMU-Pro | 기타 | 메모 |
|---|---|---|---|---|---|
| 1 | Qwen3.5 9B | 6.6GB | 70.1 | MMMU 78.4, MathVista 85.7 | 사용자가 제외 요청한 계열이지만 참고로 표기 |
| 2 | **Gemma 4 12B** | 7.6GB | 69.1 | MATH-Vision 79.7 | **qwen 외 후보 중 1위** |
| 3 | Qwen3.5 4B | 3.4GB | 66.3 | MMMU 77.6 | 작은 모델로도 근접 |
| 4 | Gemma 4 E4B | 6.1~9.6GB | 52.6 | | |
| 순위 없음 | MiniCPM-V 4.5 (8.7B) | 6.1GB | 확인 못함 | OpenCompass 77.2 | 문서·OCR에 강점이라고 소개됨. 다른 척도라 비교 불가 |
| 순위 없음 | **Ministral 3 8B / 14B** | 6.0 / 9.1GB | **확인 못함** | | 확인한 모델 카드 두 곳에 비전 점수가 없었음. AA지수(종합) 9 |

**Claude 기준선과 비교:** Sonnet 5의 MMMU 76.3, MathVista 76.6(재검증 안 된 2차 출처)에 비해 Qwen3.5 9B는 MMMU 78.4, MathVista 85.7입니다. 소형 모델이 같은 벤치마크에서 더 높게 나온다는 뜻이지만, 이런 벤치마크는 "이미지 속 문제 풀기"에 가깝고 **실제 UI 스크린샷 분석 능력과는 다를 수 있습니다.**

**⚠️ 정정:** 앞서 제가 vision 기본값으로 `ministral-3:8b`를 골랐는데, 이번 조사 결과 **근거가 되는 비전 점수를 찾지 못했습니다.** 그 선택은 "다른 계열이 궁금하다"는 요청에 맞춘 것이었고 성능 근거는 약했습니다. 증거 기준으로는 **`gemma4:12b`가 더 나은 출발점**입니다.

---

## 6. 종합: 증거 기준 추천

| 카테고리 | 사용자 선호 반영 | 근거 기준 1순위 | 현재 설정 |
|---|---|---|---|
| 추론 | `deepseek-r1:8b` (gpt-oss는 메모리 초과) | `gemma4:12b` | `deepseek-r1:8b` |
| 코딩 | vLLM에서 `devstral-small-2` / 로컬은 미정 | `gemma4:12b` (LCB 기준, 속도 미확인) | `qwen2.5-coder:7b` |
| 비전 | (qwen 제외) `gemma4:12b` | `gemma4:12b` | `ministral-3:8b` ← 근거 부족 |

**한 가지 흥미로운 점:** `gemma4:12b` 하나가 세 카테고리 모두에서 상위권입니다. 그래서 "카테고리마다 모델을 다르게 두는 것이 실제로 이득인가?"가 이 프로젝트의 핵심 실험이 될 수 있습니다. 모델을 바꿀 때마다 드는 로딩 시간(수 초)을 감수할 만큼 품질 차이가 나는지 직접 재봐야 합니다. 이건 라우팅 프로젝트의 존재 이유와도 맞닿아 있어서 좋은 보고서 주제입니다.

---

## 7. 다음 단계: 직접 측정

공개 수치는 후보를 좁히는 데까지만 쓸 수 있습니다. 다음 실험을 제안합니다.

1. **후보 5개를 받아서 같은 프롬프트로 비교**: `gemma4:12b`, `qwen3.5:9b`, `deepseek-r1:8b`, `qwen2.5-coder:7b`, `ministral-3:8b`
2. **측정 항목:** TTFT, 생성 속도(tok/s), 생각 모드 켰을 때와 껐을 때의 총 응답 시간, 최대 메모리
3. **품질은 Claude로 채점**: Sonnet 5를 심사자(judge)로 써서 각 모델의 응답을 1~5점으로 채점합니다. 이렇게 하면 "Sonnet 5 기준"이라는 요청을 **공개 벤치마크보다 훨씬 신뢰할 수 있게** 충족할 수 있습니다. 단 API 비용이 들고 키 관리가 필요하니 진행 전에 상의드리겠습니다.
4. 결과는 `docs/templates/`의 벤치마크·모델 비교 템플릿에 채워 넣습니다.

---

## 8. 출처

**Claude 기준선**
- [Anthropic: Claude Sonnet 5 발표](https://www.anthropic.com/news/claude-sonnet-5) (점수표가 이미지라 수치 미확인)
- [Anthropic: Claude Haiku 4.5 발표](https://www.anthropic.com/news/claude-haiku-4-5) (SWE-bench Verified 73.3% 확인)
- [Cosmic JS: Sonnet 5 벤치마크](https://www.cosmicjs.com/blog/claude-sonnet-5-benchmarks-pricing-developers), [Vellum: Sonnet 5 벤치마크 해설](https://www.vellum.ai/blog/claude-sonnet-5-benchmarks-explained) (2차 출처, 서로 수치가 다름)
- [BenchLM: Haiku 4.5](https://benchlm.ai/models/claude-haiku-4-5)
- [Artificial Analysis: Sonnet 5](https://artificialanalysis.ai/models/claude-sonnet-5), [Haiku 4.5](https://artificialanalysis.ai/models/claude-4-5-haiku)

**로컬 후보 모델 카드**
- [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B)
- [Gemma 4 12B](https://huggingface.co/google/gemma-4-12b-it), [Ollama gemma4](https://ollama.com/library/gemma4)
- [Ministral 3 8B](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512), [14B](https://huggingface.co/mistralai/Ministral-3-14B-Instruct-2512)
- [DeepSeek-R1-0528-Qwen3-8B](https://huggingface.co/deepseek-ai/DeepSeek-R1-0528-Qwen3-8B), [R1-Distill-Qwen-14B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B)
- [MiniCPM-V 4.5](https://huggingface.co/openbmb/MiniCPM-V-4_5)
- [Ollama devstral-small-2](https://ollama.com/library/devstral-small-2)

**크기·태그 확인 (Ollama)**
- [qwen3.5](https://ollama.com/library/qwen3.5/tags), [gemma4](https://ollama.com/library/gemma4/tags), [ministral-3](https://ollama.com/library/ministral-3/tags), [deepseek-r1](https://ollama.com/library/deepseek-r1/tags), [qwen2.5-coder](https://ollama.com/library/qwen2.5-coder/tags), [deepseek-coder-v2](https://ollama.com/library/deepseek-coder-v2/tags), [gpt-oss](https://ollama.com/library/gpt-oss/tags), [devstral-small-2](https://ollama.com/library/devstral-small-2/tags), [minicpm-v4.5](https://ollama.com/library/minicpm-v4.5)

**기타**
- [LocalLLM.in: 16GB VRAM 비교](https://localllm.in/blog/best-local-llms-16gb-vram) (gpt-oss:20b 수치, Artificial Analysis 인용)
- [InsiderLLM: 로컬 코딩 모델](https://insiderllm.com/guides/best-local-coding-models-2026/) (HumanEval 수치. 메모리 수치는 일부 부정확)
- [Artificial Analysis: Gemma 4 12B](https://artificialanalysis.ai/models/gemma-4-12b), [Ministral 3 8B](https://artificialanalysis.ai/models/ministral-3-8b), [Qwen3.5 9B](https://artificialanalysis.ai/models/qwen3-5-9b)

---

## 9. 확정 사항 (2026-09-19, 검토 후)

| 카테고리 | 확정 모델 | 크기 | 비고 |
|---|---|---|---|
| 추론 | `deepseek-r1:8b` | 5.2GB | |
| 코딩 | `devstral-small-2` | 15GB | ⚠️ 로컬 메모리 기준(≈10GB)을 넘음. 실제 속도를 측정해서 실용성을 판단하고, 너무 느리면 `qwen2.5-coder:7b`로 대체 |
| 비전 | `gemma4:12b` | 7.6GB | |

- 위 세 모델을 동시에 올리면 약 28GB라서, `OLLAMA_MAX_LOADED_MODELS=1`로 한 번에 하나씩 교체하며 씁니다. 모델이 바뀔 때마다 로딩 시간이 추가됩니다.
- 15GB 모델은 이 맥북에서 메모리 압박(스왑)이 생길 가능성이 높습니다. 이 부분은 첫 벤치마크 문서의 핵심 측정 항목입니다.
