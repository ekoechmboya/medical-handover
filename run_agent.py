"""Ablation harness for the advanced agent.

Runs the cumulative configurations
    B, B+V, B+V+D, B+V+D+R, B+V+D+R+De
across the benchmark using the PINNED baseline model (gemini-3.6-flash for real
runs; MockClient for offline plumbing validation). Ground truth is loaded only
after each case's findings are produced, and only by the scorer.

Usage:
  python run_agent.py --mode mock            # offline validation (no API)
  python run_agent.py --mode real            # real Gemini staged comparison
  python run_agent.py --mode real --configs "B" "B+V+D+R+De"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

# Load gitignored .env so GEMINI_API_KEY / MH_EMITTER_MODEL reach this process.
_env = ROOT / ".env"
if _env.is_file():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from medical_handover.agent import (  # noqa: E402
    run_pipeline,
    STAGE_VERIFY,
    STAGE_DETAIL,
    STAGE_RECONCILE,
    STAGE_DEDUP,
)
from medical_handover.llm import GeminiClient, MockClient  # noqa: E402
from medical_handover.cases import load_cases  # noqa: E402
from medical_handover.eval.ground_truth import load_ground_truth  # noqa: E402
from medical_handover.eval.scorer import score_case  # noqa: E402
from medical_handover.eval.report import aggregate  # noqa: E402

# Cumulative ablation configurations (stage flag sets).
CONFIGS = {
    "B": set(),
    "B+V": {STAGE_VERIFY},
    "B+V+D": {STAGE_VERIFY, STAGE_DETAIL},
    "B+V+D+R": {STAGE_VERIFY, STAGE_DETAIL, STAGE_RECONCILE},
    "B+V+D+R+De": {STAGE_VERIFY, STAGE_DETAIL, STAGE_RECONCILE, STAGE_DEDUP},
}

PRICING = {"prompt_per_1m_usd": 0.15, "candidates_per_1m_usd": 0.60}


class RateLimitedClient:
    """Throttle real API calls to stay under the free-tier rate limit (~20/min).

    Adds a minimum spacing between calls and retries on HTTP 429 (ResourceExhausted)
    with exponential-ish backoff. Exposes `last_usage_metadata` so token capture in
    the pipeline keeps working through the wrapper.
    """

    def __init__(self, client, min_spacing_s: float = 5.0, max_retries: int = 4):
        self._c = client
        self._min_spacing = min_spacing_s
        self._max_retries = max_retries
        self._last = 0.0
        self.last_usage_metadata = None

    def complete_json(self, prompt: str):
        import time as _t

        for attempt in range(self._max_retries):
            now = _t.time()
            wait = self._min_spacing - (now - self._last)
            if wait > 0:
                _t.sleep(wait)
            try:
                out = self._c.complete_json(prompt)
                self._last = _t.time()
                self.last_usage_metadata = getattr(self._c, "last_usage_metadata", None)
                return out
            except Exception as exc:  # noqa: BLE001
                msg = f"{type(exc).__name__}: {exc}"
                # Retry on quota (429) and transient server/timeout errors, with a
                # long growing backoff. Anything else (e.g. malformed prompt) is
                # re-raised so it is not silently swallowed.
                transient = any(
                    s in msg
                    for s in (
                        "ResourceExhausted",
                        "429",
                        "503",
                        "504",
                        "UNAVAILABLE",
                        "DEADLINE_EXCEEDED",
                        "timed out",
                        "Timeout",
                    )
                )
                if transient:
                    _t.sleep(20 + attempt * 15)
                    continue
                raise
        raise RuntimeError("RateLimitedClient: exhausted retries on API call")


def _make_client(mode: str):
    if mode == "mock":
        return MockClient()
    return RateLimitedClient(GeminiClient(temperature=0.0), min_spacing_s=5.0)


def _usage_cost(tokens_log: dict) -> float:
    cost = 0.0
    for stage, u in tokens_log.items():
        if not u:
            continue
        cost += (u.get("prompt_token_count") or 0) / 1_000_000 * PRICING["prompt_per_1m_usd"]
        cost += (u.get("candidates_token_count") or 0) / 1_000_000 * PRICING["candidates_per_1m_usd"]
    return round(cost, 4)


def run_config(name: str, enabled: set[str], cases, client, base_dir: Path) -> dict:
    cfg_dir = base_dir / name
    (cfg_dir / "cases").mkdir(parents=True, exist_ok=True)

    case_results = []
    total_runtime = 0.0
    total_tokens = {"prompt_token_count": 0, "candidates_token_count": 0, "total_token_count": 0}

    for case in cases:
        case_dir = cfg_dir / "cases" / case.case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        error = None
        try:
            res = run_pipeline(case, client, enabled=enabled)
            # Score ONLY after inference; GT never reaches the agent.
            gt = load_ground_truth(case.directory, case.case_id)
            scored = score_case(res.final, gt, difficulty=case.difficulty)
        except Exception as exc:  # noqa: BLE001
            # A failed case (e.g. API quota/timeout) must not abort the whole
            # ablation. Record the error and a zeroed result so the run still
            # completes and resumes later.
            import traceback as _tb

            error = f"{type(exc).__name__}: {exc}"
            print(f"  [warn] {case.case_id} failed: {error}", flush=True)
            _tb.print_exc()
            case_results.append(
                {
                    "case_id": case.case_id,
                    "difficulty": case.difficulty,
                    "n_expected": 0,
                    "n_predicted": 0,
                    "tp": 0,
                    "fp": 0,
                    "fn": 0,
                    "recall": 0.0,
                    "precision": 0.0,
                    "f1": 0.0,
                    "importance_recall": 0.0,
                    "status_accuracy": None,
                    "negative_violations": 0,
                    "error": error,
                    "timing_s": {},
                    "tokens": {},
                }
            )
            continue

        # Persist intermediate candidate findings after each enabled stage.
        for stage, findings in res.intermediates.items():
            (cfg_dir / "cases" / case.case_id / f"stage_{stage}.json").write_text(
                json.dumps(findings, indent=2), encoding="utf-8"
            )
        (cfg_dir / "cases" / case.case_id / "stage_log.json").write_text(
            json.dumps(res.logs, indent=2, default=str), encoding="utf-8"
        )
        (cfg_dir / "cases" / case.case_id / "result.json").write_text(
            json.dumps(
                {
                    "case_id": case.case_id,
                    "difficulty": case.difficulty,
                    "n_expected": scored.n_expected,
                    "n_predicted": scored.n_predicted,
                    "tp": scored.tp,
                    "fp": scored.fp,
                    "fn": scored.fn,
                    "recall": scored.recall,
                    "precision": scored.precision,
                    "f1": scored.f1,
                    "importance_recall": scored.importance_recall,
                    "status_accuracy": scored.status_accuracy,
                    "negative_violations": scored.negative_violations,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        total_runtime += sum(res.timing.values())
        for u in res.tokens.values():
            if u:
                for k in total_tokens:
                    total_tokens[k] += u.get(k) or 0

        case_results.append(
            {
                "case_id": case.case_id,
                "difficulty": case.difficulty,
                "n_expected": scored.n_expected,
                "n_predicted": scored.n_predicted,
                "tp": scored.tp,
                "fp": scored.fp,
                "fn": scored.fn,
                "recall": scored.recall,
                "precision": scored.precision,
                "f1": scored.f1,
                "importance_recall": scored.importance_recall,
                "status_accuracy": scored.status_accuracy,
                "negative_violations": scored.negative_violations,
                "timing_s": res.timing,
                "tokens": res.tokens,
            }
        )

    agg = {
        "config": name,
        "enabled_stages": sorted(enabled),
        "total_runtime_s": round(total_runtime, 3),
        "total_tokens": total_tokens,
        "estimated_cost_usd": _usage_cost(total_tokens),
        "aggregate": {
            "all": aggregate([_cr_to_result(c) for c in case_results]),
            "easy": aggregate([_cr_to_result(c) for c in case_results], "easy"),
            "medium": aggregate([_cr_to_result(c) for c in case_results], "medium"),
            "hard": aggregate([_cr_to_result(c) for c in case_results], "hard"),
        },
        "cases": case_results,
    }
    (cfg_dir / "results.json").write_text(json.dumps(agg, indent=2), encoding="utf-8")
    return agg


def _cr_to_result(c: dict):
    # Lightweight shim so report.aggregate can consume the per-case dicts.
    from medical_handover.eval.scorer import CaseResult

    return CaseResult(
        case_id=c["case_id"],
        difficulty=c["difficulty"],
        n_expected=c["n_expected"],
        n_predicted=c["n_predicted"],
        tp=c["tp"],
        fp=c["fp"],
        fn=c["fn"],
        recall=c["recall"],
        precision=c["precision"],
        f1=c["f1"],
        importance_recall=c["importance_recall"],
        status_accuracy=c["status_accuracy"],
        negative_violations=c["negative_violations"],
    )


def _find_saved_baseline() -> Path | None:
    candidates = sorted(ROOT.glob("reports/gemini_baseline_*/baseline_results.json"))
    return candidates[-1] if candidates else None


def _config_from_saved_baseline(saved_path: Path, base_dir: Path, name: str = "B",
                                 case_ids: set[str] | None = None) -> dict:
    """Reuse the dedicated real baseline run as ablation config B (same pinned
    model, same baseline_emit path) so we do not spend API quota re-running it.
    Filtered to `case_ids` when a case subset is being evaluated."""
    data = json.loads(saved_path.read_text(encoding="utf-8"))
    case_results = []
    for c in data["cases"]:
        if case_ids is not None and c["case_id"] not in case_ids:
            continue
        sc = c["score"]
        case_results.append(
            {
                "case_id": c["case_id"],
                "difficulty": c["difficulty"],
                "n_expected": sc["n_expected"],
                "n_predicted": sc["n_predicted"],
                "tp": sc["tp"],
                "fp": sc["fp"],
                "fn": sc["fn"],
                "recall": sc["recall"],
                "precision": sc["precision"],
                "f1": sc["f1"],
                "importance_recall": sc["importance_recall"],
                "status_accuracy": sc["status_accuracy"],
                "negative_violations": sc["negative_violations"],
                "timing_s": {"generate": c.get("runtime_s")},
                "tokens": {"generate": c.get("usage")},
            }
        )
    (base_dir / name).mkdir(parents=True, exist_ok=True)
    agg = {
        "config": name,
        "enabled_stages": [],
        "total_runtime_s": round(sum(c["runtime_s"] for c in data["cases"] if isinstance(c.get("runtime_s"), (int, float))), 3),
        "total_tokens": {
            "prompt_token_count": sum((c.get("usage") or {}).get("prompt_token_count", 0) or 0 for c in data["cases"]),
            "candidates_token_count": sum((c.get("usage") or {}).get("candidates_token_count", 0) or 0 for c in data["cases"]),
            "total_token_count": sum((c.get("usage") or {}).get("total_token_count", 0) or 0 for c in data["cases"]),
        },
        "estimated_cost_usd": _usage_cost(
            {
                "generate": {
                    "prompt_token_count": sum((c.get("usage") or {}).get("prompt_token_count", 0) or 0 for c in data["cases"]),
                    "candidates_token_count": sum((c.get("usage") or {}).get("candidates_token_count", 0) or 0 for c in data["cases"]),
                }
            }
        ),
        "aggregate": {
            "all": aggregate([_cr_to_result(c) for c in case_results]),
            "easy": aggregate([_cr_to_result(c) for c in case_results], "easy"),
            "medium": aggregate([_cr_to_result(c) for c in case_results], "medium"),
            "hard": aggregate([_cr_to_result(c) for c in case_results], "hard"),
        },
        "cases": case_results,
        "reused_from": str(saved_path),
    }
    (base_dir / name / "results.json").write_text(json.dumps(agg, indent=2), encoding="utf-8")
    return agg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["mock", "real"], required=True)
    ap.add_argument("--configs", nargs="*", default=None, help="Subset of config names")
    ap.add_argument("--cases", nargs="*", default=None)
    ap.add_argument("--out", default=str(ROOT / "reports" / "agent_ablation" / "real_run"))
    args = ap.parse_args()

    client = _make_client(args.mode)
    cases = load_cases()
    if args.cases:
        wanted = set(args.cases)
        cases = [c for c in cases if c.case_id in wanted]

    configs = CONFIGS
    if args.configs:
        configs = {k: v for k, v in CONFIGS.items() if k in set(args.configs)}

    selected_ids = set(args.cases) if args.cases else None

    base_dir = Path(args.out)
    base_dir.mkdir(parents=True, exist_ok=True)

    config_aggs = {}
    to_run = dict(configs)
    # In real mode, reuse the already-saved real baseline as config B (identical
    # pinned model + baseline_emit path) to conserve the free-tier API quota.
    if args.mode == "real" and "B" in to_run:
        saved = _find_saved_baseline()
        if saved is not None:
            print(f"[real] reusing saved real baseline as config B: {saved}", flush=True)
            config_aggs["B"] = _config_from_saved_baseline(
                saved, base_dir, "B", case_ids=selected_ids
            )
            del to_run["B"]
        else:
            print("[real] no saved baseline found; will run B via API.", flush=True)

    for name, enabled in to_run.items():
        # Resume support: skip configs already completed in this base_dir.
        if (base_dir / name / "results.json").is_file():
            print(f"[{args.mode}] config {name} already complete; resuming.", flush=True)
            config_aggs[name] = json.loads(
                (base_dir / name / "results.json").read_text(encoding="utf-8")
            )
            continue
        print(f"[{args.mode}] running config {name} (stages={sorted(enabled)}) ...", flush=True)
        config_aggs[name] = run_config(name, enabled, cases, client, base_dir)

    # Comparison across configs (per-tier + per-case F1 regression vs B).
    baseline_by_case = {c["case_id"]: c["f1"] for c in config_aggs["B"]["cases"]}
    regressions = []
    for name, agg in config_aggs.items():
        if name == "B":
            continue
        for c in agg["cases"]:
            b_f1 = baseline_by_case.get(c["case_id"])
            if b_f1 is not None and c["f1"] < b_f1 - 1e-9:
                regressions.append(
                    {"config": name, "case_id": c["case_id"], "B_f1": b_f1, "f1": c["f1"]}
                )

    comparison = {
        "mode": args.mode,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "pricing_note": "Token counts exact; cost is an ESTIMATE using PRICING constants.",
        "configs": {
            n: {
                "enabled_stages": a["enabled_stages"],
                "total_runtime_s": a["total_runtime_s"],
                "total_tokens": a["total_tokens"],
                "estimated_cost_usd": a["estimated_cost_usd"],
                "aggregate": a["aggregate"],
            }
            for n, a in config_aggs.items()
        },
        "regressions_vs_B": regressions,
    }
    (base_dir / "comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    # Console summary.
    print("\n=== ABLATION SUMMARY (macro-mean per case) ===")
    header = f"{'config':<14}{'cases':>6}{'rec':>7}{'prec':>7}{'f1':>7}{'impR':>7}{'stAcc':>7}{'FP':>5}{'FN':>5}{'rt_s':>8}{'cost$':>8}"
    print(header)
    for n, a in config_aggs.items():
        al = a["aggregate"]["all"]
        sa = "n/a" if al["status_accuracy"] is None else f"{al['status_accuracy']:.3f}"
        print(
            f"{n:<14}{al['cases']:>6}{al['recall']:>7.3f}{al['precision']:>7.3f}"
            f"{al['f1']:>7.3f}{al['importance_recall']:>7.3f}{sa:>7}{al['false_alarms']:>5}"
            f"{a['total_runtime_s']:>8.1f}{a['estimated_cost_usd']:>8.4f}"
        )
    print(f"\nPer-config details: {base_dir}")
    print(f"Regressions vs B: {len(regressions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
