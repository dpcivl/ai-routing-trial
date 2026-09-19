"""터미널 명령어 진입점.

사용 예:
  uv run ai-router check                                  # Ollama 연결 및 모델 준비 상태 확인
  uv run ai-router ask "파이썬으로 퀵정렬 짜줘"            # 라우팅 후 모델 응답까지
  uv run ai-router ask "이 화면 개선점?" --image ui.png   # 이미지 첨부 → vision 모델
  uv run ai-router ask "..." --dry-run                    # 라우팅 판단만 확인 (rule 라우터는 Ollama 불필요)
  uv run ai-router ask "..." --router llm                 # 소형 LLM 분류기로 라우팅 (Ollama 필요)
  uv run ai-router eval-routing --router llm              # 라우터 정확도 평가 + 보고서 생성

argparse는 파이썬 표준 라이브러리의 명령행 인자 파서입니다.
C의 getopt와 같은 역할을 하며, 서브커맨드(check/ask/eval-routing)도 지원합니다.
"""

import argparse
import sys
from pathlib import Path

from openai import APIConnectionError

from ai_router.backends import OpenAICompatBackend
from ai_router.config import DEFAULT_CONFIG_PATH, PROJECT_ROOT, AppConfig, load_config
from ai_router.evaluation import compute_metrics, environment_info, load_dataset, run_eval, save_outputs
from ai_router.pipeline import RoutingPipeline
from ai_router.routers import ROUTERS, Router
from ai_router.types import UserRequest

DEFAULT_DATASET = PROJECT_ROOT / "data" / "eval" / "routing_v1.jsonl"


def _make_router(name: str, config: AppConfig, backend: OpenAICompatBackend, threshold: float) -> Router:
    return ROUTERS[name].from_config(config, backend, threshold)


def cmd_check(args: argparse.Namespace, config: AppConfig) -> int:
    backend = OpenAICompatBackend(config.backend)
    print(f"백엔드 주소: {config.backend.base_url}")
    try:
        available = set(backend.list_models())
    except APIConnectionError:
        print("❌ 서버에 연결할 수 없습니다. Ollama가 실행 중인지 확인하세요. (ollama serve)")
        return 1

    # (역할 이름, 모델 이름) 목록. 라우터용 분류기도 함께 확인합니다.
    targets = [(str(category), m.name) for category, m in config.models.items()]
    if config.router_llm is not None:
        targets.append(("router_llm", config.router_llm.name))

    ok = True
    for role, model_name in targets:
        # Ollama는 "qwen3.5:9b" 형식, 태그를 생략하면 ":latest"로 취급합니다.
        name = model_name if ":" in model_name else f"{model_name}:latest"
        if name in available:
            print(f"✅ {role:<11} {model_name}")
        else:
            print(f"❌ {role:<11} {model_name}  → 설치 필요: ollama pull {model_name}")
            ok = False
    return 0 if ok else 1


def cmd_ask(args: argparse.Namespace, config: AppConfig) -> int:
    backend = OpenAICompatBackend(config.backend)
    router = _make_router(args.router, config, backend, args.threshold)
    pipeline = RoutingPipeline(router, backend, config)
    request = UserRequest(text=args.prompt, image_paths=[Path(p) for p in args.image])

    for p in request.image_paths:
        if not p.is_file():
            print(f"❌ 이미지 파일을 찾을 수 없습니다: {p}")
            return 1

    try:
        result = pipeline.run(request, dry_run=args.dry_run)
    except APIConnectionError:
        print("❌ 서버에 연결할 수 없습니다. Ollama가 실행 중인지 확인하세요. (ollama serve)")
        return 1

    d = result.decision
    model_name = config.model_for(d.category).name
    print(f"[라우팅] {d.category} → {model_name}")
    print(
        f"         라우터={d.router_name} 확신도={d.confidence:.2f} "
        f"fallback={d.is_fallback} 지연={d.latency_ms:.3f}ms"
    )
    print(f"         근거: {d.reason}")

    if result.chat is not None:
        c = result.chat
        print("\n" + "=" * 60)
        print(c.text)
        print("=" * 60)
        tps = f"{c.tokens_per_sec:.1f}" if c.tokens_per_sec else "-"
        ttft = f"{c.ttft_ms:.0f}ms" if c.ttft_ms else "-"
        print(
            f"[성능] TTFT={ttft} 전체={c.total_ms:.0f}ms "
            f"생성토큰={c.completion_tokens or '-'} 속도={tps} tok/s"
        )
    return 0


def cmd_eval_routing(args: argparse.Namespace, config: AppConfig) -> int:
    router = _make_router(args.router, config, OpenAICompatBackend(config.backend), args.threshold)
    dataset = Path(args.dataset).resolve()
    items = load_dataset(dataset)
    try:
        records = run_eval(router, items)
    except APIConnectionError:
        print("❌ 서버에 연결할 수 없습니다. --router llm 은 Ollama가 필요합니다. (ollama serve)")
        return 1
    metrics = compute_metrics(records)
    env = environment_info(dataset)

    print(f"라우터: {router.name}  데이터: {len(items)}문항")
    print(
        f"정확도: {metrics['accuracy']:.1%}  fallback: {metrics['fallback_count']}건  "
        f"평균 지연: {metrics['latency_ms']['mean']:.3f}ms"
    )

    if not args.no_save:
        json_path, md_path = save_outputs(router, env, metrics, records)
        print(f"원시 결과: {json_path.relative_to(PROJECT_ROOT)}")
        print(f"보고서:   {md_path.relative_to(PROJECT_ROOT)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-router", description="로컬 LLM 라우팅 실험 도구")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="모델 설정 YAML 경로")
    sub = parser.add_subparsers(dest="command", required=True)

    # 여러 서브커맨드가 공유하는 라우터 옵션 (llm 라우터는 Ollama 서버가 필요)
    router_opts = argparse.ArgumentParser(add_help=False)
    router_opts.add_argument("--router", choices=sorted(ROUTERS), default="rule", help="사용할 라우터")
    router_opts.add_argument(
        "--threshold", type=float, default=0.5, help="이 확신도보다 낮으면 기본 카테고리로 보냄 (0~1)"
    )

    sub.add_parser("check", help="Ollama 연결과 모델 설치 여부 확인")

    ask = sub.add_parser("ask", parents=[router_opts], help="프롬프트를 라우팅해서 모델 응답 받기")
    ask.add_argument("prompt", help="질문 내용")
    ask.add_argument("--image", action="append", default=[], help="첨부 이미지 경로 (여러 번 사용 가능)")
    ask.add_argument(
        "--dry-run",
        action="store_true",
        help="라우팅 판단만 하고 답변 모델은 호출하지 않음 (llm 라우터는 분류기용 Ollama 필요)",
    )

    ev = sub.add_parser("eval-routing", parents=[router_opts], help="라우터 정확도 평가 + 보고서 생성")
    ev.add_argument("--dataset", default=str(DEFAULT_DATASET), help="평가 데이터(JSONL) 경로")
    ev.add_argument("--no-save", action="store_true", help="결과 파일을 저장하지 않음")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(Path(args.config))
    handlers = {"check": cmd_check, "ask": cmd_ask, "eval-routing": cmd_eval_routing}
    return handlers[args.command](args, config)


if __name__ == "__main__":
    sys.exit(main())
