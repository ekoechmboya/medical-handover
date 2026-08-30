"""Tests for the advanced agent: prompt guards, GT-leakage, and stage logic."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from medical_handover.agent import (
    run_pipeline,
    STAGE_VERIFY,
    STAGE_DETAIL,
    STAGE_RECONCILE,
    STAGE_DEDUP,
)
from medical_handover.agent import verify as verify_mod
from medical_handover.agent import detail_probe as detail_mod
from medical_handover.agent.prompt_guard import assert_no_gt
from medical_handover.agent.reconcile import reconcile, PARTIAL_THRESHOLD, ABSENT_THRESHOLD
from medical_handover.agent.dedup import dedup
from medical_handover.baseline import build_prompt, baseline_emit
from medical_handover.cases import load_cases
from medical_handover.eval.ground_truth import load_ground_truth
from medical_handover.eval.scorer import score_case
from medical_handover.llm import MockClient
from medical_handover.models import Case, ClinicalRecord, Finding

import json as _json

_BASELINE_JSON = ROOT / "reports" / "gemini_baseline_20260829_110323" / "baseline_results.json"


def _baseline_findings(case_id: str):
    data = _json.loads(_BASELINE_JSON.read_text())
    by_id = {c["case_id"]: c for c in data["cases"]}
    return [
        Finding(
            category=str(p.get("category", "")),
            importance=str(p.get("importance", "high")),
            status=str(p.get("status", "omitted")),
            summary=str(p.get("summary", "")).strip(),
            evidence_sources=tuple(str(s) for s in p.get("evidence_sources", [])),
        )
        for p in by_id[case_id].get("predicted_findings", [])
    ]

CASES = load_cases()
CASE0 = CASES[0]


def _finding(summary, category="monitoring", status="omitted", evidence=("x.txt",)):
    return Finding(
        category=category,
        importance="high",
        status=status,
        summary=summary,
        evidence_sources=evidence,
    )


# ---------------------------------------------------------------------------
# prompt_guard
# ---------------------------------------------------------------------------
def test_guard_accepts_clean_prompt():
    assert_no_gt("patient profile and records and handover are fine")


def test_guard_rejects_gt_concept():
    for bad in ("ground_truth", "ground truth", "groundtruth", "ground_truth.json"):
        try:
            assert_no_gt(f"here is some {bad} text")
        except ValueError:
            pass
        else:
            raise AssertionError(f"guard did not trip on {bad!r}")


# ---------------------------------------------------------------------------
# GT-leakage: every agent prompt must pass the guard
# ---------------------------------------------------------------------------
def test_generate_prompt_has_no_gt():
    assert_no_gt(build_prompt(CASE0))


def test_verify_prompt_has_no_gt():
    cands = (_finding("monitor blood pressure", evidence=("progress_note.txt",)),)
    assert_no_gt(verify_mod.build_verify_prompt(CASE0, cands))


def test_detail_prompt_has_no_gt():
    assert_no_gt(detail_mod.build_detail_prompt(CASE0))


def test_pipeline_never_loads_ground_truth(monkeypatch):
    # If any agent stage ever imported/loaded ground truth, this would raise.
    import medical_handover.eval.ground_truth as gt_mod

    def _boom(*a, **k):
        raise AssertionError("agent loaded ground truth during inference!")

    monkeypatch.setattr(gt_mod, "load_ground_truth", _boom)
    client = MockClient()
    enabled = {STAGE_VERIFY, STAGE_DETAIL, STAGE_RECONCILE, STAGE_DEDUP}
    res = run_pipeline(CASE0, client, enabled=enabled)
    assert isinstance(res.final, tuple)
    # generate stage must equal a direct baseline call
    assert len(res.intermediates["generate"]) == len(baseline_emit(CASE0, MockClient()))


# ---------------------------------------------------------------------------
# stage logic units
# ---------------------------------------------------------------------------
def _mini_case(handover_text: str) -> Case:
    return Case(
        case_id="t",
        title="t",
        difficulty="easy",
        patient_id="p",
        age=1,
        sex="m",
        admission_reason="r",
        current_location="ward",
        directory=Path("."),
        handover=ClinicalRecord("current_handover.txt", handover_text),
        records=(),
    )


def test_reconcile_high_coverage_is_partially_omitted():
    case = _mini_case("the blood pressure target is 120-140 mmHg and monitor closely")
    f = _finding("blood pressure target 120-140 mmHg")
    rr = reconcile((f,), case, semantic={0: "omitted"})
    assert rr.findings[0].status == "partially_omitted"
    assert rr.changes[0]["conflict"] is True  # semantic said omitted, coverage overrode


def test_reconcile_low_coverage_is_omitted():
    # Post-verify state: finding already carries the semantic status. Handover
    # shares no content tokens -> decisive ABSENT band overrides to "omitted".
    case = _mini_case("patient is comfortable and stable")
    f = _finding("no anticoagulants without neurology approval", status="partially_omitted")
    rr = reconcile((f,), case, semantic={0: "partially_omitted"})
    assert rr.findings[0].status == "omitted"
    assert rr.changes[0]["conflict"] is True


def test_reconcile_ambiguous_band_preserves_semantic():
    # ~moderate overlap (0.15 < cov < 0.5) -> ambiguous band -> preserve Stage 3
    # semantic result ("partially_omitted"), no conflict recorded.
    case = _mini_case("the patient has an anticoagulant restriction in place")
    f = _finding("no anticoagulant without neurology approval", status="omitted")
    rr = reconcile((f,), case, semantic={0: "partially_omitted"})
    assert rr.findings[0].status == "partially_omitted"
    assert rr.changes[0]["conflict"] is False


def test_reconcile_unverified_uses_band_only():
    case = _mini_case("the target is 120-140 mmHg")
    f = _finding("blood pressure target 120-140 mmHg")
    rr = reconcile((f,), case)  # no semantic mapping
    assert rr.findings[0].status == "partially_omitted"


def test_dedup_merges_redundant():
    f1 = _finding("continue telemetry overnight", evidence=("progress_note.txt",))
    f2 = _finding("continue telemetry overnight as planned", evidence=("progress_note.txt",))
    dr = dedup((f1, f2))
    assert len(dr.findings) == 1
    assert len(dr.removed) == 1


def test_verify_applies_verdicts_without_api():
    # Canned client returning a verdict that prunes candidate 0 and keeps 1.
    class FakeClient:
        def complete_json(self, prompt):
            assert_no_gt(prompt)
            return {
                "verdicts": [
                    {"index": 0, "keep": False, "reason": "already in handover"},
                    {"index": 1, "keep": True, "category": "medication", "status": "omitted"},
                ]
            }

    cands = (
        _finding("bp monitoring", evidence=("progress_note.txt",)),
        _finding("warfarin held", category="medication", evidence=("medication_orders.txt",)),
    )
    vr = verify_mod.verify_batch(CASE0, cands, FakeClient())
    kept = [d for d in vr.decisions if d.kept]
    assert len(kept) == 1
    assert vr.decisions[0].kept is False
    assert vr.removed[0]["reason"] == "already in handover"


def test_verify_applies_importance_correction():
    class FakeClient:
        def complete_json(self, prompt):
            return {
                "verdicts": [
                    {"index": 0, "keep": True, "category": "monitoring",
                     "status": "partially_omitted", "importance": "critical"},
                ]
            }

    cands = (_finding("blood pressure target 120-140", category="monitoring"),)
    vr = verify_mod.verify_batch(CASE0, cands, FakeClient())
    assert vr.decisions[0].kept is True
    assert vr.decisions[0].finding.importance == "critical"
    assert vr.decisions[0].finding.status == "partially_omitted"


def test_dedup_merges_on_shared_evidence_and_unions_evidence():
    f1 = _finding("continue telemetry overnight", evidence=("progress_note.txt",))
    f2 = _finding("continue telemetry overnight as planned", evidence=("progress_note.txt", "nursing_note.txt"))
    dr = dedup((f1, f2))
    assert len(dr.findings) == 1
    # evidence of the merged (higher-importance-equal) finding is the union
    assert set(dr.findings[0].evidence_sources) == {"progress_note.txt", "nursing_note.txt"}


def test_reconcile_improves_status_accuracy_on_saved_baseline():
    # Regression lock for the measured offline win: applying RECONCILE to the real
    # saved Gemini baseline raises status_accuracy with no precision/recall loss.
    base_status, base_rec, base_prec = [], [], []
    rec_status, rec_rec, rec_prec = [], [], []
    for case in CASES:
        cands = _baseline_findings(case.case_id)
        gt = load_ground_truth(case.directory, case.case_id)
        b = score_case(tuple(cands), gt, difficulty=case.difficulty)
        r = score_case(reconcile(tuple(cands), case).findings, gt, difficulty=case.difficulty)
        if b.status_accuracy is not None:
            base_status.append(b.status_accuracy)
            rec_status.append(r.status_accuracy)
        base_rec.append(b.recall); rec_rec.append(r.recall)
        base_prec.append(b.precision); rec_prec.append(r.precision)
    assert sum(rec_status) / len(rec_status) >= sum(base_status) / len(base_status)
    assert sum(rec_rec) / len(rec_rec) >= sum(base_rec) / len(base_rec) - 1e-9
    assert sum(rec_prec) / len(rec_prec) >= sum(base_prec) / len(base_prec) - 1e-9
