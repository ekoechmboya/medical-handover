from __future__ import annotations

import json
from pathlib import Path

import pytest

from medical_handover.baseline import baseline_emit, build_prompt
from medical_handover.eval.ground_truth import load_ground_truth
from medical_handover.llm import MockClient
from medical_handover.models import Case, Finding
from medical_handover.schema import CATEGORIES, STATUSES, canonical_category

pytestmark = pytest.mark.usefixtures("force_mock_backend")


@pytest.fixture
def force_mock_backend(monkeypatch):
    monkeypatch.setenv("MH_EMITTER_BACKEND", "mock")


def _all_cases():
    from medical_handover.cases import load_cases

    return load_cases()


class _CapturingClient:
    def __init__(self, payload):
        self.payload = payload
        self.prompts: list[str] = []

    def complete_json(self, prompt: str) -> dict:
        self.prompts.append(prompt)
        return self.payload


def test_baseline_returns_schema_valid_findings():
    for case in _all_cases():
        findings = baseline_emit(case)
        assert isinstance(findings, tuple)
        for f in findings:
            assert isinstance(f, Finding)
            assert f.category in CATEGORIES, f"{case.case_id}: bad category {f.category!r}"
            assert f.status in STATUSES, f"{case.case_id}: bad status {f.status!r}"
            assert f.summary.strip(), f"{case.case_id}: empty summary"
            allowed = {r.filename for r in case.records} | {case.handover.filename}
            for src in f.evidence_sources:
                assert src in allowed, f"{case.case_id}: evidence {src!r} not in inputs"


def test_baseline_canonicalizes_aliased_categories():
    case = _all_cases()[0]
    client = _CapturingClient(
        {
            "findings": [
                {
                    "category": "monitoring_target",  # aliased form
                    "importance": "high",
                    "status": "omitted",
                    "summary": "Blood pressure target omitted.",
                    "evidence_sources": [case.records[0].filename],
                }
            ]
        }
    )
    findings = baseline_emit(case, client=client)
    assert findings[0].category == canonical_category("monitoring_target") == "monitoring"
    assert findings[0].status == "omitted"


def test_baseline_normalizes_invalid_status_to_omitted():
    case = _all_cases()[0]
    client = _CapturingClient(
        {
            "findings": [
                {
                    "category": "medication",
                    "importance": "high",
                    "status": "unsupported_garbage",
                    "summary": "Anticoagulant omitted.",
                    "evidence_sources": [case.records[0].filename],
                }
            ]
        }
    )
    findings = baseline_emit(case, client=client)
    assert findings[0].status == "omitted"


def test_ground_truth_is_never_loaded_by_baseline():
    # If baseline ever reached for ground truth, this would raise.
    def _boom(*a, **k):
        raise AssertionError("baseline_emit touched ground truth!")

    import medical_handover.baseline as baseline_mod  # noqa: F401

    # Patch at the only place it could be imported from.
    import medical_handover.eval.ground_truth as gt_mod

    original = gt_mod.load_ground_truth
    gt_mod.load_ground_truth = _boom
    try:
        for case in _all_cases():
            baseline_emit(case)  # must not invoke load_ground_truth
    finally:
        gt_mod.load_ground_truth = original


def test_ground_truth_never_appears_in_prompt():
    for case in _all_cases():
        client = _CapturingClient(
            {"findings": []}
        )
        baseline_emit(case, client=client)
        prompt = client.prompts[-1]
        assert "ground_truth" not in prompt
        assert "ground truth" not in prompt.lower()

        gt = load_ground_truth(case.directory, case.case_id)
        for f in gt.expected_findings:
            # None of the gold-standard expected_text may leak into the prompt.
            assert f.expected_text not in prompt, (
                f"{case.case_id}: GT expected_text leaked into prompt"
            )
        # The raw GT file content must not be embedded either.
        gt_path = case.directory / "ground_truth.json"
        assert gt_path.read_text(encoding="utf-8") not in prompt


def test_mock_client_is_deterministic():
    case = _all_cases()[0]
    a = json.dumps(MockClient().complete_json(build_prompt(case)), sort_keys=True)
    b = json.dumps(MockClient().complete_json(build_prompt(case)), sort_keys=True)
    assert a == b
