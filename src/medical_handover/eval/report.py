from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from .scorer import CaseResult


def format_case_table(results: Sequence[CaseResult]) -> str:
    header = (
        f"{'case':<10}{'diff':<8}{'exp':>4}{'pred':>5}{'TP':>4}{'FP':>4}{'FN':>4}"
        f"{'rec':>7}{'prec':>7}{'F1':>7}{'wRec':>7}{'stAcc':>7}{'negV':>6}"
    )
    rows = [header, "-" * len(header)]
    for r in results:
        status_acc = "n/a" if r.status_accuracy is None else f"{r.status_accuracy:.2f}"
        rows.append(
            f"{r.case_id:<10}{r.difficulty:<8}{r.n_expected:>4}{r.n_predicted:>5}"
            f"{r.tp:>4}{r.fp:>4}{r.fn:>4}{r.recall:>7.3f}{r.precision:>7.3f}"
            f"{r.f1:>7.3f}{r.importance_recall:>7.3f}{status_acc:>7}{r.negative_violations:>6}"
        )
    return "\n".join(rows)


def aggregate(results: Sequence[CaseResult], difficulty: str | None = None) -> dict:
    subset = results if difficulty is None else [r for r in results if r.difficulty == difficulty]
    count = len(subset)
    if count == 0:
        return {"difficulty": difficulty or "all", "cases": 0, "recall": 0.0, "precision": 0.0, "f1": 0.0}
    return {
        "difficulty": difficulty or "all",
        "cases": count,
        "recall": sum(r.recall for r in subset) / count,
        "precision": sum(r.precision for r in subset) / count,
        "f1": sum(r.f1 for r in subset) / count,
        "importance_recall": sum(r.importance_recall for r in subset) / count,
        "false_alarms": sum(r.fp for r in subset),
        "status_accuracy": (
            sum(r.status_accuracy for r in subset if r.status_accuracy is not None)
            / sum(1 for r in subset if r.status_accuracy is not None)
            if any(r.status_accuracy is not None for r in subset)
            else None
        ),
    }


def format_summary(results: Sequence[CaseResult]) -> str:
    overall = aggregate(results)
    tiers = ["easy", "medium", "hard"]
    lines = ["", "=== Aggregate (macro-mean, per-case) ==="]
    lines.append(_format_row(overall))
    for tier in tiers:
        agg = aggregate(results, tier)
        if agg["cases"]:
            lines.append(_format_row(agg))
    return "\n".join(lines)


def _format_row(agg: dict) -> str:
    status_acc = "n/a" if agg["status_accuracy"] is None else f"{agg['status_accuracy']:.3f}"
    return (
        f"  {agg['difficulty']:<8} cases={agg['cases']:>2}  recall={agg['recall']:.3f}  "
        f"precision={agg['precision']:.3f}  f1={agg['f1']:.3f}  "
        f"importance_recall={agg['importance_recall']:.3f}  status_acc={status_acc}  "
        f"total_false_alarms={agg['false_alarms']}"
    )


def export_to_json(meta: dict, results: Sequence[CaseResult], path: Path) -> None:
    payload = {
        "meta": meta,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "aggregates": {
            "all": aggregate(results),
            "easy": aggregate(results, "easy"),
            "medium": aggregate(results, "medium"),
            "hard": aggregate(results, "hard"),
        },
        "cases": [
            {
                "case_id": r.case_id,
                "difficulty": r.difficulty,
                "n_expected": r.n_expected,
                "n_predicted": r.n_predicted,
                "tp": r.tp,
                "fp": r.fp,
                "fn": r.fn,
                "recall": r.recall,
                "precision": r.precision,
                "f1": r.f1,
                "importance_recall": r.importance_recall,
                "status_accuracy": r.status_accuracy,
                "negative_violations": r.negative_violations,
                "matched_findings": [
                    {
                        "predicted_index": m.predicted_index,
                        "finding_id": m.finding.finding_id,
                        "score": m.score,
                    }
                    for m in r.matches
                ],
            }
            for r in results
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")