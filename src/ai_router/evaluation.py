"""라우터 정확도 평가 + 결과 문서(Markdown) 자동 생성.

흐름:
  data/eval/*.jsonl (정답이 달린 프롬프트)
      → 라우터로 하나씩 판단
      → 정답과 비교해 지표 계산
      → results/routing/*.json   (원시 결과: 나중에 다시 분석할 수 있도록 모두 저장)
      → docs/routing/*.md        (사람이 읽는 보고서)

지표 설명:
  - 정확도(accuracy): 전체 중 맞힌 비율
  - 정밀도(precision): "coding이라고 판단한 것" 중 실제로 coding인 비율
                       → 낮으면 엉뚱한 요청이 코딩 모델로 많이 간다는 뜻
  - 재현율(recall):    "실제 coding인 것" 중 coding으로 판단한 비율
                       → 낮으면 코딩 요청을 놓치고 있다는 뜻
  - 혼동 행렬(confusion matrix): 행=정답, 열=판단. 어떤 카테고리끼리 헷갈리는지 한눈에 보임
"""

import hashlib
import json
import platform
import statistics
import subprocess
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from ai_router.config import PROJECT_ROOT
from ai_router.routers.base import Router
from ai_router.types import Category, RouteDecision, UserRequest


class EvalItem(BaseModel):
    """평가 데이터 한 줄 (JSONL의 한 행)."""

    id: str
    text: str
    expected: Category
    images: list[str] = []  # 라우팅 평가에서는 "이미지가 있는지"만 중요하므로 실제 파일이 없어도 됩니다.
    note: str = ""  # 이 문항을 넣은 의도 (예: "함정 문제")


class EvalRecord(BaseModel):
    item: EvalItem
    decision: RouteDecision

    @property
    def correct(self) -> bool:
        return self.item.expected == self.decision.category


def load_dataset(path: Path) -> list[EvalItem]:
    items = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                items.append(EvalItem.model_validate_json(line))
            except Exception as e:
                raise ValueError(f"{path}:{line_no} 형식 오류: {e}") from e
    return items


def run_eval(router: Router, items: list[EvalItem]) -> list[EvalRecord]:
    records = []
    for item in items:
        request = UserRequest(text=item.text, image_paths=[Path(p) for p in item.images])
        records.append(EvalRecord(item=item, decision=router.route(request)))
    return records


def compute_metrics(records: list[EvalRecord]) -> dict:
    cats = list(Category)
    # confusion[정답][판단] = 개수
    confusion = {e: {p: 0 for p in cats} for e in cats}
    for r in records:
        confusion[r.item.expected][r.decision.category] += 1

    per_category = {}
    for c in cats:
        tp = confusion[c][c]  # 정답 c, 판단 c
        predicted = sum(confusion[e][c] for e in cats)  # 판단이 c인 전체
        actual = sum(confusion[c].values())  # 정답이 c인 전체
        per_category[c.value] = {
            "precision": tp / predicted if predicted else None,
            "recall": tp / actual if actual else None,
            "support": actual,
        }

    latencies = sorted(r.decision.latency_ms for r in records)
    p95_index = max(0, int(len(latencies) * 0.95) - 1)
    return {
        "total": len(records),
        "correct": sum(r.correct for r in records),
        "accuracy": sum(r.correct for r in records) / len(records),
        "fallback_count": sum(r.decision.is_fallback for r in records),
        "latency_ms": {
            "mean": statistics.mean(latencies),
            "p95": latencies[p95_index],
            "max": latencies[-1],
        },
        "per_category": per_category,
        "confusion": {e.value: {p.value: n for p, n in row.items()} for e, row in confusion.items()},
    }


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown (커밋 전)"


def environment_info(dataset_path: Path) -> dict:
    """재현성을 위한 실행 환경 기록. 같은 결과를 다시 얻으려면 이 정보가 필요합니다."""
    return {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "dataset": str(dataset_path.relative_to(PROJECT_ROOT))
        if dataset_path.is_relative_to(PROJECT_ROOT)
        else str(dataset_path),
        # 데이터셋이 바뀌었는지 확인하기 위한 지문(해시)
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest()[:12],
        "python": platform.python_version(),
        "machine": f"{platform.system()} {platform.machine()} {platform.mac_ver()[0]}",
    }


def _fmt(v: float | None) -> str:
    return "-" if v is None else f"{v:.2f}"


def render_markdown(router: Router, env: dict, metrics: dict, records: list[EvalRecord]) -> str:
    cats = [c.value for c in Category]
    lines = [
        f"# 라우팅 평가 결과: `{router.name}` 라우터",
        "",
        "> 이 문서는 `ai-router eval-routing` 명령으로 자동 생성되었습니다. 직접 수정하지 마세요.",
        "> 분석/의견은 별도 문서에 작성하는 것을 권장합니다.",
        "",
        "## 실행 환경",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        *[f"| {k} | `{v}` |" for k, v in env.items()],
        f"| confidence_threshold | `{router.confidence_threshold}` |",
        f"| default_category | `{router.default_category}` |",
        "",
        "## 요약",
        "",
        "| 지표 | 값 |",
        "|---|---|",
        f"| 정확도 | **{metrics['accuracy']:.1%}** ({metrics['correct']}/{metrics['total']}) |",
        f"| fallback 발생 | {metrics['fallback_count']}건 |",
        f"| 라우팅 지연 (평균) | {metrics['latency_ms']['mean']:.3f} ms |",
        f"| 라우팅 지연 (p95) | {metrics['latency_ms']['p95']:.3f} ms |",
        "",
        "## 카테고리별 성능",
        "",
        "| 카테고리 | 정밀도 | 재현율 | 문항 수 |",
        "|---|---|---|---|",
        *[
            f"| {c} | {_fmt(m['precision'])} | {_fmt(m['recall'])} | {m['support']} |"
            for c, m in metrics["per_category"].items()
        ],
        "",
        "## 혼동 행렬",
        "",
        "행 = 정답, 열 = 라우터 판단. 대각선(굵은 글씨)이 맞힌 개수입니다.",
        "",
        "| 정답 \\ 판단 | " + " | ".join(cats) + " |",
        "|---|" + "---|" * len(cats),
    ]
    for e in cats:
        row = metrics["confusion"][e]
        cells = [f"**{row[p]}**" if p == e else str(row[p]) for p in cats]
        lines.append(f"| {e} | " + " | ".join(cells) + " |")

    wrong = [r for r in records if not r.correct]
    lines += ["", f"## 오답 목록 ({len(wrong)}건)", ""]
    if wrong:
        lines += ["| ID | 프롬프트 | 정답 | 판단 | 확신도 | 근거 |", "|---|---|---|---|---|---|"]
        for r in wrong:
            text = r.item.text.replace("|", "\\|").replace("\n", " ")
            text = text if len(text) <= 60 else text[:57] + "..."
            reason = r.decision.reason.replace("|", "\\|")
            lines.append(
                f"| {r.item.id} | {text} | {r.item.expected} | {r.decision.category} "
                f"| {r.decision.confidence:.2f} | {reason} |"
            )
    else:
        lines.append("오답 없음")
    return "\n".join(lines) + "\n"


def save_outputs(router: Router, env: dict, metrics: dict, records: list[EvalRecord]) -> tuple[Path, Path]:
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    json_path = PROJECT_ROOT / "results" / "routing" / f"{stamp}_{router.name}.json"
    md_path = PROJECT_ROOT / "docs" / "routing" / f"{stamp}_{router.name}.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "router": router.name,
        "environment": env,
        "metrics": metrics,
        "records": [
            {"item": r.item.model_dump(mode="json"), "decision": r.decision.model_dump(mode="json")}
            for r in records
        ],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(router, env, metrics, records), encoding="utf-8")
    return json_path, md_path
