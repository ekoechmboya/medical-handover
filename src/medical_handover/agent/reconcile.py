"""Stage 5 — RECONCILE status + canonical category (rule-based, no LLM call).

Sets each finding's status to 'omitted' vs 'partially_omitted' using a
deterministic token-coverage signal, while preserving the Stage 3 semantic
verifier's decision where it is appropriate to do so.

Conflict resolution policy (documented for auditability)
-------------------------------------------------------
Let `cov` = fraction of the finding's content tokens present in the handover
(0 = handover says nothing about it, 1 = handover already states it). Let
`sem` = the semantic status decided by the VERIFY stage (None for findings that
were never verified, e.g. those added by DETAIL).

  * If cov >= PARTIAL_THRESHOLD (0.50): the handover clearly already covers the
    item -> resolved = 'partially_omitted' (deterministic, overrides sem).
  * If cov <= ABSENT_THRESHOLD (0.15): the handover clearly lacks the item ->
    resolved = 'omitted' (deterministic, overrides sem).
  * Otherwise (0.15 < cov < 0.50, the ambiguous band): clinical information is
    often PARAPHRASED, so token coverage is unreliable. Here we PRESERVE the
    Stage 3 semantic verification result (`resolved = sem`). This is exactly the
    "preserve semantic result where appropriate" case.

A `conflict` is recorded whenever the resolved status differs from `sem` (only
possible in the two deterministic bands, where coverage is decisive). Canonical
category is always re-applied via `canonical_category`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import Case, Finding
from ..schema import canonical_category

PARTIAL_THRESHOLD = 0.50
ABSENT_THRESHOLD = 0.15

_TOKEN_RE = __import__("re").compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "if", "then", "of", "in", "on",
        "for", "with", "to", "from", "at", "by", "as", "is", "are", "was",
        "were", "be", "been", "not", "no", "do", "does", "did", "has", "have",
        "had", "it", "its", "this", "that", "these", "those", "they", "them",
        "we", "our", "who", "what", "which", "when", "where", "how", "will",
        "would", "can", "could", "should", "may", "might", "must", "current",
        "currently", "due", "because", "remain", "remains", "remaining",
        "under", "during", "over", "still", "now", "patient", "note", "notes",
    }
)


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def coverage(summary: str, handover: str) -> float:
    ts, th = _tokens(summary), _tokens(handover)
    if not ts:
        return 1.0
    return len(ts & th) / len(ts)


@dataclass
class ReconcileResult:
    findings: tuple[Finding, ...] = ()
    changes: tuple[dict, ...] = ()  # {index, category, summary, old_status, new_status, cov, semantic, conflict}


def reconcile(
    findings: tuple[Finding, ...], case: Case, semantic: dict[int, str] | None = None
) -> ReconcileResult:
    semantic = semantic or {}
    new: list[Finding] = []
    changes: list[dict] = []
    handover = case.handover.text

    for i, f in enumerate(findings):
        cov = coverage(f.summary, handover)
        # `sem` is the Stage 3 semantic decision, present only for findings that
        # were actually verified. DETAIL-sourced findings have no semantic
        # decision and fall back purely to the coverage band rule.
        sem = semantic.get(i)

        if cov >= PARTIAL_THRESHOLD:
            resolved = "partially_omitted"
        elif cov <= ABSENT_THRESHOLD:
            resolved = "omitted"
        else:
            resolved = sem if sem is not None else "omitted"

        conflict = (sem is not None and resolved != sem)
        category = canonical_category(f.category)
        updated = Finding(
            category=category,
            importance=f.importance,
            status=resolved,
            summary=f.summary,
            evidence_sources=f.evidence_sources,
        )
        if updated.status != f.status or updated.category != f.category:
            changes.append(
                {
                    "index": i,
                    "category": category,
                    "summary": f.summary,
                    "old_status": f.status,
                    "new_status": resolved,
                    "old_category": f.category,
                    "cov": round(cov, 3),
                    "semantic": sem,
                    "conflict": conflict,
                }
            )
        new.append(updated)

    return ReconcileResult(findings=tuple(new), changes=tuple(changes))
