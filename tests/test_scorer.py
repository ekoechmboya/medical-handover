from medical_handover.cases import load_cases
from medical_handover.eval.ground_truth import load_ground_truth
from medical_handover.eval.probes import null_emit, oracle_emit
from medical_handover.eval.scorer import (
    MATCH_THRESHOLD,
    evidence_jaccard,
    match_score,
    score_case,
    token_recall,
)
from medical_handover.models import Finding


def _gt(case):
    return load_ground_truth(case.directory, case.case_id)


def test_oracle_achieves_perfect_score_on_every_case():
    for case in load_cases():
        result = score_case(oracle_emit(case), _gt(case), difficulty=case.difficulty)
        assert result.tp == result.n_expected, case.case_id
        assert result.fp == 0, case.case_id
        assert result.fn == 0, case.case_id
        assert result.recall == 1.0, case.case_id
        assert result.precision == 1.0, case.case_id
        assert result.f1 == 1.0, case.case_id
        assert result.importance_recall == 1.0, case.case_id
        if result.n_expected:
            assert result.status_accuracy == 1.0, case.case_id


def test_null_emit_scores_zero_recall_and_no_false_alarms():
    for case in load_cases():
        result = score_case(null_emit(case), _gt(case), difficulty=case.difficulty)
        assert result.n_predicted == 0
        assert result.fp == 0
        if _gt(case).expected_findings:
            assert result.recall == 0.0
            assert result.f1 == 0.0
        else:
            assert result.recall == 1.0
            assert result.precision == 1.0
            assert result.f1 == 1.0


def test_false_positive_control_case_zeroes_precision_when_findings_emitted():
    case_07 = next(c for c in load_cases() if c.case_id == "case_07")
    junk = (
        Finding(
            category="medication",
            importance="high",
            status="omitted",
            summary="Anticoagulant change is missing from handover.",
        ),
    )
    result = score_case(junk, _gt(case_07), difficulty=case_07.difficulty)
    assert result.n_expected == 0
    assert result.fp == 1
    assert result.precision == 0.0
    assert result.f1 == 0.0


def test_unrelated_findings_produce_no_matches():
    case = next(c for c in load_cases() if c.case_id == "case_01")
    junk = (
        Finding(
            category="documentation",
            importance="low",
            status="omitted",
            summary="Patient meal preferences were not documented in the discharge letter.",
            evidence_sources=("progress_note.txt",),
        ),
    )
    result = score_case(junk, _gt(case), difficulty=case.difficulty)
    assert result.tp == 0
    assert result.fn == 1
    assert result.recall == 0.0


def test_partial_status_gets_credit_but_less_than_exact():
    case = next(c for c in load_cases() if c.case_id == "case_01")
    best = _gt(case).expected_findings[0]
    exact = Finding(best.category, best.importance, best.status, best.expected_text, best.evidence_sources)
    partial = Finding(best.category, best.importance, "partially_omitted", best.expected_text, best.evidence_sources)
    wrong = Finding(best.category, best.importance, "unsupported", best.expected_text, best.evidence_sources)
    assert match_score(exact, best) >= MATCH_THRESHOLD
    assert match_score(partial, best) >= MATCH_THRESHOLD
    assert match_score(partial, best) < match_score(exact, best)
    assert match_score(wrong, best) < match_score(partial, best)


def test_token_recall_and_evidence_jaccard():
    assert token_recall("systolic blood pressure target 120", "systolic blood pressure target is 120") > 0.9
    assert token_recall("one to one supervision", "dietician review requested") == 0.0
    assert evidence_jaccard(["a.txt", "b.txt"], ["a.txt"]) == 0.5
    assert evidence_jaccard([], []) == 1.0


def test_case_result_counts_are_consistent():
    for case in load_cases():
        result = score_case(oracle_emit(case), _gt(case), difficulty=case.difficulty)
        assert result.tp + result.fp == result.n_predicted
        assert result.tp + result.fn == result.n_expected


def test_oracle_never_trips_negative_violations():
    for case in load_cases():
        result = score_case(oracle_emit(case), _gt(case), difficulty=case.difficulty)
        assert result.negative_violations == 0, case.case_id


def test_false_positive_overlapping_negative_counts_as_violation():
    case_01 = next(c for c in load_cases() if c.case_id == "case_01")
    inventor = (
        Finding(
            category="monitoring",
            importance="medium",
            status="omitted",
            summary="Oxygen saturation monitoring was not instructed in the handover.",
            evidence_sources=(),
        ),
    )
    result = score_case(inventor, _gt(case_01), difficulty=case_01.difficulty)
    assert result.tp == 0
    assert result.fp == 1
    assert result.negative_violations == 1