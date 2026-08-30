"""Stage 6 — DEDUP (rule-based, no LLM call).

Prunes redundant findings: when two findings share a canonical category and an
evidence source and have high summary overlap, they are merged into a single
finding (the higher-importance one is kept). This removes near-duplicate
candidates that the one-shot baseline and the DETAIL probe may both surface for
the same underlying omission.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..models import Finding
from ..schema import canonical_category

_OVERLAP_THRESHOLD = 0.7
_IMPORTANCE_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}

_TOKEN_RE = re.compile(r"[a-z0-9]+")
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


def _overlap(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


@dataclass
class DedupResult:
    findings: tuple[Finding, ...] = ()
    removed: tuple[dict, ...] = ()  # {index, category, summary, merged_into, reason}


def dedup(findings: tuple[Finding, ...]) -> DedupResult:
    kept: list[Finding] = []
    removed: list[dict] = []
    # Work by index so we can report which were merged/removed.
    pending = list(enumerate(findings))

    for i, f in pending:
        cat = canonical_category(f.category)
        merged = False
        for j, k in enumerate(kept):
            kcat = canonical_category(k.category)
            if kcat != cat:
                continue
            ov = _overlap(f.summary, k.summary)
            shared_ev = bool(set(f.evidence_sources) & set(k.evidence_sources))
            # Merge when the two findings are clearly the same underlying omission:
            #  - high summary overlap (regardless of evidence), or
            #  - same cited evidence with moderate overlap.
            if ov >= 0.85 or (shared_ev and ov >= 0.5) or (shared_ev and ov >= 0.4 and not f.evidence_sources):
                # Merge into the higher-importance kept finding, unioning evidence
                # so the surviving finding keeps the most complete citation.
                if _IMPORTANCE_RANK.get(f.importance, 0) >= _IMPORTANCE_RANK.get(k.importance, 0):
                    kept[j] = Finding(
                        category=cat,
                        importance=f.importance,
                        status=k.status if f.status == k.status else f.status,
                        summary=k.summary if ov >= 0.85 else f.summary,
                        evidence_sources=tuple(sorted(set(f.evidence_sources) | set(k.evidence_sources))),
                    )
                removed.append(
                    {
                        "index": i,
                        "category": cat,
                        "summary": f.summary,
                        "merged_into_index": j,
                        "reason": "duplicate of kept finding (same category; high overlap or shared evidence)",
                    }
                )
                merged = True
                break
        if not merged:
            kept.append(f)

    return DedupResult(findings=tuple(kept), removed=tuple(removed))
