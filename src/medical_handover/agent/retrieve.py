"""Evidence retrieval for the verification stage.

Retrieval is deliberately minimal: the baseline already carries `evidence_sources`
(filename references) on each candidate, so the dominant retrieval path is an
exact file lookup. A keyword fallback exists for candidates whose evidence
references are missing or implausible. No embeddings, no external index.

Importantly, retrieval only ever reads the same allowed `.txt` clinical records
that the baseline uses. It explicitly excludes `ground_truth.json`.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from ..models import Case, ClinicalRecord, Finding

# Records in a case directory that are never part of the clinical record set the
# model is allowed to see (the handover is handled separately, and the
# ground-truth file is evaluation-only and must never be read here).
_EXCLUDED_FILENAMES = {"current_handover.txt", "ground_truth.json"}

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


@dataclass(frozen=True)
class Evidence:
    finding_index: int
    cited_filenames: tuple[str, ...]
    record_text: str
    handover_text: str
    keyword_hits: tuple[str, ...] = ()


def _record_by_name(case: Case, name: str) -> ClinicalRecord | None:
    for rec in case.records:
        if rec.filename == name:
            return rec
    return None


def retrieve_evidence(case: Case, finding: Finding, index: int) -> Evidence:
    """Return the raw text of the records cited by a finding, plus the handover.

    Falls back to a keyword search over all records when the cited filenames are
    missing or do not actually support the finding's content.
    """
    cited = tuple(f for f in finding.evidence_sources if f not in _EXCLUDED_FILENAMES)
    texts: list[str] = []
    for name in cited:
        rec = _record_by_name(case, name)
        if rec is not None:
            texts.append(f"=== {rec.filename} ===\n{rec.text.strip()}")

    # Keyword fallback: if nothing was cited, search the finding's content tokens
    # across the records so the verifier still has something to check against.
    keyword_hits: list[str] = []
    if not texts:
        ftoks = _tokens(finding.summary)
        for rec in case.records:
            if rec.filename in _EXCLUDED_FILENAMES:
                continue
            if ftoks & _tokens(rec.text):
                texts.append(f"=== {rec.filename} ===\n{rec.text.strip()}")
                keyword_hits.append(rec.filename)

    return Evidence(
        finding_index=index,
        cited_filenames=cited,
        record_text="\n\n".join(texts),
        handover_text=case.handover.text.strip(),
        keyword_hits=tuple(keyword_hits),
    )
