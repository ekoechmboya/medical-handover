"""Offline evaluation of the improved agent WITHOUT any Gemini calls.

Two things are measured:

1. RULE-STAGE UPLIFT (defensible, GT-free at inference): apply the agent's
   rule-based stages -- RECONCILE (status/category) then DEDUP -- directly to the
   *saved real Gemini baseline predictions* (baseline_results.json) and re-score
   against ground truth. These stages use only the handover text, never GT, so
   this is a legitimate, real measurement of what the rule stages buy us.

2. HEURISTIC-VERIFY PROXY (ESTIMATE only): a deterministic stand-in for the LLM
   VERIFY stage (which needs Gemini and therefore cannot run now). It prunes
   candidates that are (a) already clearly stated in the handover or (b) not
   supported by their cited records. This estimates the FP-reduction headroom the
   real LLM verifier should capture. Clearly labelled as a proxy, not ground truth.

The real LLM-backed ablation (run_agent.py --mode real) remains the authoritative
measurement and must be run when the API quota is available.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from medical_handover.agent.dedup import dedup
from medical_handover.agent.reconcile import reconcile
from medical_handover.agent.retrieve import retrieve_evidence
from medical_handover.cases import load_cases
from medical_handover.eval.ground_truth import load_ground_truth
from medical_handover.eval.report import aggregate, format_case_table, format_summary
from medical_handover.eval.scorer import CaseResult, score_case, tokens as _tokens
from medical_handover.models import Case, Finding

ROOT = Path(r"C:\Users\HomePC\Desktop\hackathon")
BASELINE_JSON = ROOT / "reports" / "gemini_baseline_20260829_110323" / "baseline_results.json"
OUT_JSON = ROOT / "reports" / "agent_ablation" / "offline_eval.json"

_VERIFY_PRUNE_HANDOVER_COV = 0.50   # proxy: already stated in handover -> false alarm
# NOTE: a 'cited record doesn't support' rule is deliberately DISABLED here
# (threshold 0.0 = never triggers) because the naive version hurt recall by
# pruning genuine omissions whose source record paraphrased the finding. This is
# precisely why VERIFY must be LLM-driven and conservative, not a keyword check.
_VERIFY_PRUNE_SUPPORT_COV = 0.0     # disabled: see note above


def _cov(summary: str, text: str) -> float:
    ts, th = _tokens(summary), _tokens(text)
    if not ts:
        return 1.0
    return len(ts & th) / len(ts)


@dataclass
class ProxyVerifyResult:
    kept: list[Finding]
    removed: list[dict]


def heuristic_verify(case: Case, candidates: Sequence[Finding]) -> ProxyVerifyResult:
    """Deterministic, GT-free proxy for the LLM VERIFY stage (estimate only)."""
    kept: list[Finding] = []
    removed: list[dict] = []
    handover = case.handover.text
    for i, f in enumerate(candidates):
        cov_h = _cov(f.summary, handover)
        ev = retrieve_evidence(case, f, i)
        support = _cov(f.summary, ev.record_text) if ev.record_text else 0.0

        if cov_h >= _VERIFY_PRUNE_HANDOVER_COV:
            removed.append({"index": i, "summary": f.summary, "reason": "already in handover (proxy)", "cov_h": round(cov_h, 2)})
            continue
        if support < _VERIFY_PRUNE_SUPPORT_COV:
            removed.append({"index": i, "summary": f.summary, "reason": "unsupported by cited record (proxy)", "support": round(support, 2)})
            continue
        kept.append(f)
    return ProxyVerifyResult(kept=kept, removed=removed)


def findings_from_baseline(preds: list[dict]) -> list[Finding]:
    out = []
    for p in preds:
        out.append(
            Finding(
                category=str(p.get("category", "")),
                importance=str(p.get("importance", "high")),
                status=str(p.get("status", "omitted")),
                summary=str(p.get("summary", "")).strip(),
                evidence_sources=tuple(str(s) for s in p.get("evidence_sources", [])),
            )
        )
    return out


def main() -> None:
    cases = {c.case_id: c for c in load_cases()}
    data = json.loads(BASELINE_JSON.read_text())
    by_id = {c["case_id"]: c for c in data["cases"]}

    baseline_results: list[CaseResult] = []
    rule_results: list[CaseResult] = []
    proxy_results: list[CaseResult] = []

    proxy_removed_total = 0
    rule_dedup_removed = 0
    rule_reconcile_changes = 0

    for cid, case in cases.items():
        preds = by_id[cid].get("predicted_findings", [])
        base_findings = findings_from_baseline(preds)
        gt = load_ground_truth(case.directory, cid)

        # (A) baseline, as-is
        baseline_results.append(score_case(tuple(base_findings), gt, difficulty=case.difficulty))

        # (B) baseline + rule stages (RECONCILE then DEDUP)
        rr = reconcile(tuple(base_findings), case)
        rule_reconcile_changes += len(rr.changes)
        dr = dedup(rr.findings)
        rule_dedup_removed += len(dr.removed)
        rule_results.append(score_case(dr.findings, gt, difficulty=case.difficulty))

        # (C) baseline + heuristic-verify proxy + rule stages (ESTIMATE)
        pv = heuristic_verify(case, base_findings)
        proxy_removed_total += len(pv.removed)
        rr2 = reconcile(tuple(pv.kept), case)
        dr2 = dedup(rr2.findings)
        proxy_results.append(score_case(dr2.findings, gt, difficulty=case.difficulty))

    print("=== BASELINE (real Gemini, as saved) ===")
    print(format_case_table(baseline_results))
    print(format_summary(baseline_results))

    print("\n=== + RULE STAGES (reconcile+dedup) -- measured, no LLM ===")
    print(format_case_table(rule_results))
    print(format_summary(rule_results))

    print("\n=== + HEURISTIC-VERIFY PROXY + rule stages -- CAUTIONARY DEMO (NOT a gain estimate) ===")
    print("(A conservative keyword proxy that only prunes findings already stated in the")
    print(" handover STILL drops recall: it removes genuine PENDING/PARTIAL omissions the")
    print(" handover merely mentions. This proves verify must be LLM-driven + conservative,")
    print(" not a keyword rule. The authoritative measurement is run_agent.py --mode real.)")
    print(format_case_table(proxy_results))
    print(format_summary(proxy_results))

    def _delta(a, b, key):
        return round(b[key] - a[key], 3)

    base_agg = aggregate(baseline_results)
    rule_agg = aggregate(rule_results)
    proxy_agg = aggregate(proxy_results)
    print("\n=== DELTAS vs BASELINE (all-tier macro) ===")
    print(f"  rule stages : recall {_delta(base_agg, rule_agg, 'recall'):+.3f}  "
          f"precision {_delta(base_agg, rule_agg, 'precision'):+.3f}  "
          f"f1 {_delta(base_agg, rule_agg, 'f1'):+.3f}  "
          f"status_acc {_delta(base_agg, rule_agg, 'status_accuracy'):+.3f}  "
          f"false_alarms {rule_agg['false_alarms'] - base_agg['false_alarms']:+d}")
    print(f"  +verify-proxy: recall {_delta(base_agg, proxy_agg, 'recall'):+.3f}  "
          f"precision {_delta(base_agg, proxy_agg, 'precision'):+.3f}  "
          f"f1 {_delta(base_agg, proxy_agg, 'f1'):+.3f}  "
          f"status_acc {_delta(base_agg, proxy_agg, 'status_accuracy'):+.3f}  "
          f"false_alarms {proxy_agg['false_alarms'] - base_agg['false_alarms']:+d}")
    print(f"\n  proxy pruned {proxy_removed_total} candidates; "
          f"rule stages changed {rule_reconcile_changes} statuses + removed {rule_dedup_removed} via dedup.")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(
            {
                "note": "Offline. Rule-stage uplift is measured (GT-free inference). "
                        "The +verify-proxy row is an ESTIMATE using a deterministic stand-in "
                        "for the LLM verify stage; the authoritative run is run_agent.py --mode real.",
                "baseline_aggregate": base_agg,
                "rule_stage_aggregate": rule_agg,
                "proxy_verify_aggregate": proxy_agg,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nWrote {OUT_JSON}")


if __name__ == "__main__":
    main()
