from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from ..models import Finding, GroundTruth, GroundTruthFinding
from ..schema import CATEGORY_ALIASES, canonical_category

_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "if", "then", "of", "in", "on",
    "for", "with", "to", "from", "at", "by", "as", "is", "are", "was",
    "were", "be", "been", "not", "no", "do", "does", "did", "has", "have",
    "had", "it", "its", "this", "that", "these", "those", "they", "them",
    "we", "our", "who", "what", "which", "when", "where", "how", "will",
    "would", "can", "could", "should", "may", "might", "must", "current",
    "currently", "due", "because", "remain", "remains", "remaining", "under",
    "during", "over", "still", "now", "then",
})

_TOKEN_RE = re.compile(r"[a-z0-9]+")

IMPORTANCE_WEIGHT = {"critical": 1.0, "high": 0.5, "medium": 0.25, "low": 0.1}
STATUS_WEIGHT = {"omitted": 1.0, "partially_omitted": 0.5}

# Canonical category map now lives in medical_handover.schema; re-exported here
# for backwards compatibility. It folds both raw and aliased ground-truth
# spellings onto a single canonical vocabulary shared with the model prompt.


MATCH_THRESHOLD = 0.5
TEXT_RECALL_FULL = 0.4
EVIDENCE_FULL = 0.5
NEGATIVE_VIOLATION_OVERLAP = 0.35


def tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def token_recall(expected: str, summary: str) -> float:
    exp, summ = tokens(expected), tokens(summary)
    if not exp:
        return 1.0
    return len(exp & summ) / len(exp)


def evidence_jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def _norm_category(category: str) -> str:
    return canonical_category(category)


def match_score(pred: Finding, gt: GroundTruthFinding) -> float:
    score = 0.0
    if _norm_category(pred.category) == _norm_category(gt.category):
        score += 0.35
    iw_p = IMPORTANCE_WEIGHT.get(pred.importance, 0.0)
    iw_g = IMPORTANCE_WEIGHT.get(gt.importance, 0.0)
    score += 0.10 * (1.0 - abs(iw_p - iw_g))
    sw_p = STATUS_WEIGHT.get(pred.status, 0.0)
    sw_g = STATUS_WEIGHT.get(gt.status, 0.0)
    score += 0.15 * (1.0 - abs(sw_p - sw_g))
    text_recall = token_recall(gt.expected_text, pred.summary)
    score += 0.25 * min(1.0, text_recall / TEXT_RECALL_FULL)
    jaccard = evidence_jaccard(pred.evidence_sources, gt.evidence_sources)
    score += 0.15 * min(1.0, jaccard / EVIDENCE_FULL)
    return score


@dataclass(frozen=True)
class FindingMatch:
    predicted_index: int
    finding: GroundTruthFinding
    score: float


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    difficulty: str
    n_expected: int
    n_predicted: int
    tp: int
    fp: int
    fn: int
    recall: float
    precision: float
    f1: float
    importance_recall: float
    status_accuracy: float | None
    negative_violations: int
    matches: tuple[FindingMatch, ...] = field(default=())


def score_case(
    predictions: Sequence[Finding],
    gt: GroundTruth,
    difficulty: str = "",
) -> CaseResult:
    candidates: list[tuple[float, int, int]] = []
    for pi, pred in enumerate(predictions):
        for gi, gt_finding in enumerate(gt.expected_findings):
            if token_recall(gt_finding.expected_text, pred.summary) == 0.0:
                continue
            score = match_score(pred, gt_finding)
            if score >= MATCH_THRESHOLD:
                candidates.append((score, pi, gi))

    candidates.sort(key=lambda t: (t[0], -t[1], -t[2]), reverse=True)
    used_pred: set[int] = set()
    used_gt: set[int] = set()
    matches: list[FindingMatch] = []
    for score, pi, gi in candidates:
        if pi in used_pred or gi in used_gt:
            continue
        used_pred.add(pi)
        used_gt.add(gi)
        matches.append(FindingMatch(predicted_index=pi, finding=gt.expected_findings[gi], score=score))
    matches.sort(key=lambda m: m.predicted_index)
    return _build_result(predictions, gt, matches, difficulty)


def _build_result(
    predictions: Sequence[Finding],
    gt: GroundTruth,
    matches: list[FindingMatch],
    difficulty: str,
) -> CaseResult:
    n_expected = len(gt.expected_findings)
    n_predicted = len(predictions)
    tp = len(matches)
    fn = n_expected - tp
    fp = n_predicted - tp

    recall = tp / n_expected if n_expected else 1.0
    precision = tp / n_predicted if n_predicted else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    matched_weights = sum(IMPORTANCE_WEIGHT.get(m.finding.importance, 0.0) for m in matches)
    total_weights = sum(IMPORTANCE_WEIGHT.get(f.importance, 0.0) for f in gt.expected_findings)
    importance_recall = matched_weights / total_weights if total_weights else 1.0

    if matches:
        status_accuracy = sum(
            1.0 for m in matches if predictions[m.predicted_index].status == m.finding.status
        ) / len(matches)
    else:
        status_accuracy = None

    matched_indices = {m.predicted_index for m in matches}
    unmatched_indices = set(range(n_predicted)) - matched_indices
    negative_violations = count_negative_violations(
        gt.negative_findings,
        predictions,
        unmatched_indices,
    )

    return CaseResult(
        case_id=gt.case_id,
        difficulty=difficulty,
        n_expected=n_expected,
        n_predicted=n_predicted,
        tp=tp,
        fp=fp,
        fn=fn,
        recall=recall,
        precision=precision,
        f1=f1,
        importance_recall=importance_recall,
        status_accuracy=status_accuracy,
        negative_violations=negative_violations,
        matches=tuple(matches),
    )


def count_negative_violations(
    negatives: Sequence[str],
    predictions: Sequence[Finding],
    unmatched_predicted_indices: set[int],
) -> int:
    """Count false-positive findings that overlap a ground-truth negative statement.

    Only unmatched (i.e., false-positive) predictions are considered, so a true
    positive that happens to share concept words with a negative statement is
    never penalized. Heuristic, diagnostic-only; precision is the primary
    false-positive guard.
    """
    violations = 0
    for index in unmatched_predicted_indices:
        pred_tokens = tokens(predictions[index].summary)
        if not pred_tokens:
            continue
        for negative in negatives:
            neg_tokens = tokens(negative)
            if not neg_tokens:
                continue
            overlap = len(neg_tokens & pred_tokens) / len(neg_tokens)
            if overlap >= NEGATIVE_VIOLATION_OVERLAP:
                violations += 1
                break
    return violations