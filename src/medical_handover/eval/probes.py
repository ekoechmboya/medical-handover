from __future__ import annotations

from ..models import Case, Finding
from .ground_truth import load_ground_truth


def oracle_emit(case: Case) -> tuple[Finding, ...]:
    """Calibration probe ONLY: emits the ground truth verbatim.

    Used to prove the scorer is correct (expected upper bound = 1.0 across the
    board) and to sanity-check the matching pipeline. Never used to evaluate a
    real system.
    """
    gt = load_ground_truth(case.directory, case.case_id)
    return tuple(
        Finding(
            category=f.category,
            importance=f.importance,
            status=f.status,
            summary=f.expected_text,
            evidence_sources=f.evidence_sources,
        )
        for f in gt.expected_findings
    )


def null_emit(case: Case) -> tuple[Finding, ...]:
    """Calibration probe ONLY: emits no findings.

    Expected lower bound: zero recall on cases that have findings, and no false
    alarms on the false-positive control case.
    """
    return ()