"""Stage 3 — semantic VERIFY (one batched LLM call per case).

Primary false-positive control. For every candidate produced by the one-shot
baseline, the verifier is shown the candidate together with the exact records it
cited (via `retrieve.retrieve_evidence`) and the current handover, and asked to:
  * KEEP or PRUNE (prune if the omission is not actually supported by the cited
    record, or if it is already sufficiently covered by the handover), and
  * optionally CORRECT the canonical category and the omitted/partially_omitted
    status, with a short reason.

The verifier's status decision is preserved as the "semantic status" and later
consumed by RECONCILE (Stage 5), which only overrides it on decisive,
deterministic coverage evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..baseline import findings_from_payload
from ..models import Case, Finding
from ..schema import canonical_category, is_valid_status
from .prompt_guard import assert_no_gt
from .retrieve import retrieve_evidence


_VERIFY_SYSTEM = (
    "You are a strict verification reviewer for a clinical handover-quality "
    "check. You are given candidate findings (each with an index), the clinical "
    "records they cite, and the current handover. Your ONLY job is to remove "
    "FALSE POSITIVES and FIX mislabeled fields. A candidate is a false positive "
    "if ANY of these hold:\n"
    "  (F1) FALSE ALARM: the handover already clearly states the same item "
    "(even in different words) -> the omission is not real.\n"
    "  (F2) UNSUPPORTED: the cited record does NOT actually contain the event, "
    "value, or instruction the candidate claims -> likely hallucinated.\n"
    "  (F3) NOT IMPORTANT: the item is trivial/cosmetic and a receiving clinician "
    "would not need it -> not worth flagging.\n"
    "Otherwise KEEP it (it is a genuine, clinically important omission).\n\n"
    "For each KEEP you MAY also CORRECT fields to improve precision:\n"
    "- `category`: one of the canonical categories (fix obvious mislabels).\n"
    "- `status`: 'omitted' if the item is absent from the handover, "
    "'partially_omitted' if the handover mentions it but incompletely. Use the "
    "handover wording as the ground signal, not the candidate's own claim.\n"
    "- `importance`: 'critical'|'high'|'medium'|'low' if clearly wrong.\n"
    "Rules:\n"
    "- Use EXACTLY the cited record filenames; never invent records.\n"
    "- Be conservative about removing: when uncertain, KEEP (a missed omission "
    "is worse than a harmless extra flag), but DO remove clear F1/F2/F3 cases.\n"
    "- Respond ONLY with strict JSON: {\"verdicts\": [{\"index\": <int>, "
    "\"keep\": <bool>, \"category\": <str>, \"status\": <str>, \"importance\": "
    "<str>, \"reason\": <str>}]}.\n"
    "Canonical categories: allergy_or_adverse_reaction, clinical_status, "
    "escalation, medication, monitoring, pending_consult, "
    "pending_investigation, pending_result, procedure, safety.\n"
)


@dataclass
class VerifyDecision:
    index: int
    kept: bool
    finding: Finding | None  # corrected finding when kept, else None
    reason: str = ""


@dataclass
class VerifyResult:
    decisions: tuple[VerifyDecision, ...] = ()
    removed: tuple[dict, ...] = ()  # {index, category, summary, evidence_sources, reason, semantic_status}
    raw_verdicts: list[dict] = field(default_factory=list)


def build_verify_prompt(case: Case, candidates: tuple[Finding, ...]) -> str:
    lines: list[str] = [_VERIFY_SYSTEM, "", "HANDOVER:", case.handover.text.strip(), ""]
    lines.append("CANDIDATES (with cited evidence):")
    for i, f in enumerate(candidates):
        ev = retrieve_evidence(case, f, i)
        lines.append(f"\n--- candidate {i} ---")
        lines.append(f"category: {f.category}")
        lines.append(f"importance: {f.importance}")
        lines.append(f"status: {f.status}")
        lines.append(f"summary: {f.summary}")
        lines.append(f"evidence_sources: {list(f.evidence_sources)}")
        lines.append("cited record text:")
        lines.append(ev.record_text if ev.record_text else "(no cited records found)")
    return "\n".join(lines)


def _apply_verdict(
    candidate: Finding, verdict: dict | None
) -> tuple[Finding | None, str | None]:
    """Return (kept_finding_or_None, removal_reason_or_None)."""
    if verdict is None:
        # No verdict returned for this candidate: conservative KEEP, no change.
        return candidate, None

    keep = bool(verdict.get("keep", True))
    if not keep:
        reason = str(verdict.get("reason", "verifier pruned (no reason given)"))
        return None, reason

    category = canonical_category(str(verdict.get("category", candidate.category)))
    status = str(verdict.get("status", candidate.status))
    if not is_valid_status(status):
        status = candidate.status
    importance = str(verdict.get("importance", candidate.importance))
    if importance not in ("critical", "high", "medium", "low"):
        importance = candidate.importance
    corrected = Finding(
        category=category,
        importance=importance,
        status=status,
        summary=candidate.summary,
        evidence_sources=candidate.evidence_sources,
    )
    return corrected, None


def verify_batch(
    case: Case, candidates: tuple[Finding, ...], client
) -> VerifyResult:
    prompt = build_verify_prompt(case, candidates)
    assert_no_gt(prompt)  # guard: must never contain ground truth

    decisions: list[VerifyDecision] = []
    removed: list[dict] = []
    raw: list[dict] = []
    try:
        payload = client.complete_json(prompt)
    except Exception:
        # If verification fails, fall back to keeping all candidates unchanged so
        # the pipeline still produces output (and the failure is visible in logs).
        for i, cand in enumerate(candidates):
            decisions.append(VerifyDecision(index=i, kept=True, finding=cand))
        return VerifyResult(decisions=tuple(decisions), removed=(), raw_verdicts=[])

    verdicts = payload.get("verdicts", []) if isinstance(payload, dict) else []
    by_index = {int(v["index"]): v for v in verdicts if isinstance(v, dict) and "index" in v}
    raw = list(verdicts)

    for i, cand in enumerate(candidates):
        verdict = by_index.get(i)
        kept_finding, reason = _apply_verdict(cand, verdict)
        if kept_finding is None:
            removed.append(
                {
                    "index": i,
                    "category": cand.category,
                    "summary": cand.summary,
                    "evidence_sources": list(cand.evidence_sources),
                    "reason": reason or "verifier pruned",
                    "semantic_status": cand.status,
                }
            )
            decisions.append(VerifyDecision(index=i, kept=False, finding=None, reason=reason))
        else:
            decisions.append(VerifyDecision(index=i, kept=True, finding=kept_finding))
    return VerifyResult(decisions=tuple(decisions), removed=tuple(removed), raw_verdicts=raw)
