"""Run the REAL Gemini baseline against the synthetic benchmark.

Ground truth is opened ONLY after Gemini has produced findings for a case, and
is never passed to the model. This script is evidence-preserving: it writes a
timestamped directory under reports/ containing the master JSON summary, the
raw model payloads, and the exact prompts sent to Gemini.

Usage:
  python run_real_baseline.py
  python run_real_baseline.py --model gemini-3.6-flash
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

# --- Load local .env (gitignored) so the key reaches this fresh process. ---
_env_path = ROOT / ".env"
if _env_path.is_file():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# --- Imports (after env is set so GeminiClient can read GEMINI_API_KEY). ---
from medical_handover.llm import GeminiClient  # noqa: E402
from medical_handover.baseline import build_prompt, findings_from_payload  # noqa: E402
from medical_handover.cases import load_cases  # noqa: E402
from medical_handover.eval.ground_truth import load_ground_truth  # noqa: E402
from medical_handover.eval.scorer import score_case, CaseResult  # noqa: E402
from medical_handover.eval.report import aggregate  # noqa: E402


# Approximate published flash-tier rates (USD per 1M tokens). LABELED ESTIMATE:
# replace with your account/region rates if they differ. Token counts are exact;
# the cost figures are derived from them using these constants.
ESTIMATED_PRICING = {"prompt_per_1m_usd": 0.15, "candidates_per_1m_usd": 0.60}


def usage_to_dict(um) -> dict | None:
    if um is None:
        return None
    return {
        "prompt_token_count": getattr(um, "prompt_token_count", None),
        "candidates_token_count": getattr(um, "candidates_token_count", None),
        "total_token_count": getattr(um, "total_token_count", None),
    }


def finding_to_dict(f) -> dict:
    return {
        "category": f.category,
        "importance": f.importance,
        "status": f.status,
        "summary": f.summary,
        "evidence_sources": list(f.evidence_sources),
    }


def main() -> int:
    model = os.environ.get("MH_EMITTER_MODEL", "gemini-3.6-flash")
    temperature = 0.0

    client = GeminiClient(model=model, temperature=temperature)
    cases = load_cases()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = ROOT / "reports" / f"gemini_baseline_{stamp}"
    (export_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (export_dir / "responses").mkdir(parents=True, exist_ok=True)

    case_results: list[CaseResult] = []
    per_case_records: list[dict] = []
    total_prompt_tokens = 0
    total_candidates_tokens = 0
    total_runtime_s = 0.0
    errors: list[str] = []

    for case in cases:
        # 1) Build prompt strictly from allowed inputs (NO ground truth).
        prompt = build_prompt(case)
        (export_dir / "prompts" / f"{case.case_id}.txt").write_text(
            prompt, encoding="utf-8"
        )

        # 2) Call Gemini BEFORE touching ground truth.
        t0 = time.perf_counter()
        error: str | None = None
        payload: object = {}
        try:
            payload = client.complete_json(prompt)
        except Exception as exc:  # keep going; record failure as evidence
            error = f"{type(exc).__name__}: {exc}"
            errors.append(f"{case.case_id}: {error}")
            traceback.print_exc()
        elapsed = time.perf_counter() - t0
        total_runtime_s += elapsed

        usage = usage_to_dict(client.last_usage_metadata)
        if usage:
            total_prompt_tokens += usage["prompt_token_count"] or 0
            total_candidates_tokens += usage["candidates_token_count"] or 0

        # Persist the raw model response for evidence/reproducibility.
        (export_dir / "responses" / f"{case.case_id}.json").write_text(
            json.dumps(
                {"error": error, "usage": usage, "payload": payload},
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        # 3) ONLY NOW score against ground truth (never fed to the model).
        findings = findings_from_payload(payload) if not error else ()
        ground_truth = load_ground_truth(case.directory, case.case_id)
        result = score_case(findings, ground_truth, difficulty=case.difficulty)
        case_results.append(result)

        per_case_records.append(
            {
                "case_id": case.case_id,
                "difficulty": case.difficulty,
                "runtime_s": round(elapsed, 3),
                "usage": usage,
                "error": error,
                "predicted_findings": [finding_to_dict(f) for f in findings],
                "score": {
                    "n_expected": result.n_expected,
                    "n_predicted": result.n_predicted,
                    "tp": result.tp,
                    "fp": result.fp,
                    "fn": result.fn,
                    "recall": result.recall,
                    "precision": result.precision,
                    "f1": result.f1,
                    "importance_recall": result.importance_recall,
                    "status_accuracy": result.status_accuracy,
                    "negative_violations": result.negative_violations,
                    "matched_findings": [
                        {
                            "predicted_index": m.predicted_index,
                            "finding_id": m.finding.finding_id,
                            "score": round(m.score, 4),
                        }
                        for m in result.matches
                    ],
                },
            }
        )

        print(
            f"{case.case_id:<10} diff={case.difficulty:<7} "
            f"exp={result.n_expected:>2} pred={result.n_predicted:>2} "
            f"TP={result.tp:>2} FP={result.fp:>2} FN={result.fn:>2} "
            f"rec={result.recall:.2f} prec={result.precision:.2f} "
            f"F1={result.f1:.2f} t={elapsed:.1f}s "
            f"tok={usage['prompt_token_count'] if usage else '?'}"
            + (f" ERR={error}" if error else "")
        )

    total_tokens = total_prompt_tokens + total_candidates_tokens
    est_cost_usd = (
        total_prompt_tokens / 1_000_000 * ESTIMATED_PRICING["prompt_per_1m_usd"]
        + total_candidates_tokens / 1_000_000 * ESTIMATED_PRICING["candidates_per_1m_usd"]
    )

    agg = {
        "model": model,
        "temperature": temperature,
        "pricing_note": "Token counts exact; cost is an ESTIMATE using ESTIMATED_PRICING.",
        "estimated_pricing_usd_per_1m": ESTIMATED_PRICING,
        "total_cases": len(case_results),
        "total_runtime_s": round(total_runtime_s, 3),
        "total_prompt_tokens": total_prompt_tokens,
        "total_candidates_tokens": total_candidates_tokens,
        "total_tokens": total_tokens,
        "estimated_total_cost_usd": round(est_cost_usd, 4),
        "aggregate": {
            "all": aggregate(case_results),
            "easy": aggregate(case_results, "easy"),
            "medium": aggregate(case_results, "medium"),
            "hard": aggregate(case_results, "hard"),
        },
        "errors": errors,
    }

    master = {
        "meta": {
            "run_type": "real_gemini_baseline",
            "model": model,
            "temperature": temperature,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "gt_leakage": "ground_truth read only after inference; never sent to model",
        },
        "summary": agg,
        "cases": per_case_records,
    }

    master_path = export_dir / "baseline_results.json"
    master_path.write_text(json.dumps(master, indent=2), encoding="utf-8")

    print("\n=== Aggregate (macro-mean, per-case) ===")
    for tier in ("all", "easy", "medium", "hard"):
        a = agg["aggregate"][tier]
        if not a["cases"]:
            continue
        sa = "n/a" if a["status_accuracy"] is None else f"{a['status_accuracy']:.3f}"
        print(
            f"  {tier:<7} cases={a['cases']:>2} recall={a['recall']:.3f} "
            f"precision={a['precision']:.3f} f1={a['f1']:.3f} "
            f"imp_recall={a['importance_recall']:.3f} status_acc={sa} "
            f"false_alarms={a['false_alarms']}"
        )
    print(f"\nTotal runtime: {total_runtime_s:.1f}s | tokens: {total_tokens} "
          f"(prompt {total_prompt_tokens} / out {total_candidates_tokens}) | "
          f"est. cost ${est_cost_usd:.4f}")
    print(f"Exported: {master_path}")
    if errors:
        print(f"WARNING: {len(errors)} case(s) had API errors (see export).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
