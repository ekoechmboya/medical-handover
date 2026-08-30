"""API tests for the Medical Handover Quality Agent Django backend.

Run with:  python backend/manage.py test handovers
"""

from __future__ import annotations

import json
import os
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Analysis, Finding, FindingReview

PROFILE = {
    "case_id": "demo_01",
    "title": "Demo penicillin allergy omitted",
    "difficulty": "easy",
    "patient_id": "SYN-DEMO-1",
    "age": 58,
    "sex": "F",
    "admission_reason": "Community-acquired pneumonia",
    "current_location": "Medical Ward A",
}

RECORDS = [
    {
        "filename": "admission_note.txt",
        "content": (
            "Admission Note - 2026-08-28 08:10\n"
            "The patient has a severe penicillin allergy. "
            "No anticoagulant without haematology approval. "
            "Monitor blood pressure and oxygen saturation. "
            "The patient must be escalated if the GCS drops below 12. "
            "Awaiting microbiology culture results."
        ),
    }
]

HANDOVER = "Patient is stable."


def default_payload(mode: str = "baseline") -> dict:
    return {
        "patient_profile": PROFILE,
        "records": RECORDS,
        "handover": HANDOVER,
        "mode": mode,
    }


class AnalysisApiTests(TestCase):
    @classmethod
    def setUpClass(cls):
        # The project .env now sets MH_EMITTER_BACKEND=gemini; tests must stay
        # offline and deterministic, so force the mock emitter for this suite.
        super().setUpClass()
        cls._env_backend = mock.patch.dict(
            os.environ, {"MH_EMITTER_BACKEND": "mock"}
        )
        cls._env_backend.start()

    @classmethod
    def tearDownClass(cls):
        cls._env_backend.stop()
        super().tearDownClass()

    def setUp(self):
        self.client = APIClient()

    # ------------------------------------------------------------------
    # creating + retrieving analyses
    # ------------------------------------------------------------------
    def test_create_analysis_baseline(self):
        resp = self.client.post("/api/analyses/", default_payload("baseline"), format="json")
        assert resp.status_code == 201, resp.data

        body = resp.data
        assert body["status"] == "completed"
        assert body["mode"] == "baseline"
        assert body["id"] > 0
        assert "created_at" in body and "updated_at" in body
        assert body["patient_profile"]["case_id"] == "demo_01"
        assert body["handover"] == HANDOVER

        findings = body["findings"]
        assert len(findings) == 5
        first = findings[0]
        assert set(
            {"id", "order", "category", "importance", "status", "summary",
             "evidence_sources", "original", "evidence", "review"}
        ) <= set(first.keys())
        assert first["category"] in {
            "allergy_or_adverse_reaction", "medication", "monitoring",
            "escalation", "pending_result",
        }
        assert first["status"] in {"omitted", "partially_omitted"}
        assert all(f["evidence_sources"] == ["admission_note.txt"] for f in findings)
        # resolved evidence resolves back to submitted record content
        assert first["evidence"][0]["filename"] == "admission_note.txt"
        assert "penicillin allergy" in first["evidence"][0]["content"]

    def test_create_analysis_advanced_with_mock(self):
        resp = self.client.post("/api/analyses/", default_payload("advanced"), format="json")
        assert resp.status_code == 201, resp.data
        body = resp.data
        assert body["status"] == "completed"
        assert body["mode"] == "advanced"
        assert body["engine_meta"]["stages"] == [
            "generate", "verify", "detail", "reconcile", "dedup",
        ]
        assert len(body["findings"]) >= 1

    def test_list_analyses(self):
        self.client.post("/api/analyses/", default_payload("baseline"), format="json")
        self.client.post("/api/analyses/", default_payload("advanced"), format="json")
        resp = self.client.get("/api/analyses/")
        assert resp.status_code == 200
        assert resp.data["count"] == 2
        assert {r["mode"] for r in resp.data["results"]} == {"baseline", "advanced"}
        for item in resp.data["results"]:
            assert item["finding_count"] >= 1
            assert "review_summary" in item

    def test_retrieve_analysis_detail(self):
        created = self.client.post(
            "/api/analyses/", default_payload("advanced"), format="json"
        ).data
        resp = self.client.get(f"/api/analyses/{created['id']}/")
        assert resp.status_code == 200
        body = resp.data
        assert body["id"] == created["id"]
        assert body["mode"] == "advanced"
        assert body["records"] == RECORDS
        assert body["review_summary"]["total"] == len(body["findings"])

    def test_analysis_not_found(self):
        resp = self.client.get("/api/analyses/999999/")
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # human review workflow
    # ------------------------------------------------------------------
    def _create_and_get_findings(self):
        body = self.client.post(
            "/api/analyses/", default_payload("baseline"), format="json"
        ).data
        return body["id"], body["findings"]

    def test_accept_finding(self):
        analysis_id, findings = self._create_and_get_findings()
        fid = findings[0]["id"]
        resp = self.client.post(
            f"/api/analyses/{analysis_id}/findings/{fid}/review/",
            {"decision": "accepted", "comment": "Confirmed by reviewer"},
            format="json",
        )
        assert resp.status_code == 200, resp.data
        assert resp.data["decision"] == "accepted"
        assert resp.data["comment"] == "Confirmed by reviewer"

        detail = self.client.get(f"/api/analyses/{analysis_id}/").data
        reviewed = detail["findings"][0]
        assert reviewed["review"]["decision"] == "accepted"
        # original AI finding untouched
        assert reviewed["original"] == {
            "category": reviewed["category"],
            "importance": reviewed["importance"],
            "status": reviewed["status"],
            "summary": reviewed["summary"],
            "evidence_sources": reviewed["evidence_sources"],
        }

    def test_reject_finding(self):
        analysis_id, findings = self._create_and_get_findings()
        fid = findings[1]["id"]
        resp = self.client.post(
            f"/api/analyses/{analysis_id}/findings/{fid}/review/",
            {"decision": "rejected", "comment": "Already covered in verbal handover"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["decision"] == "rejected"

    def test_edit_finding_preserves_original_ai_output(self):
        analysis_id, findings = self._create_and_get_findings()
        fid = findings[0]["id"]
        original = Finding.objects.get(pk=fid)
        ai_summary = original.original_data["summary"]

        resp = self.client.post(
            f"/api/analyses/{analysis_id}/findings/{fid}/review/",
            {
                "decision": "edited",
                "edited_summary": "Penicillin allergy (anaphylaxis) omitted from handover.",
                "edited_category": "allergy_or_adverse_reaction",
                "edited_status": "partially_omitted",
                "comment": "Clarified severity.",
            },
            format="json",
        )
        assert resp.status_code == 200, resp.data
        assert resp.data["decision"] == "edited"
        assert resp.data["edited_summary"].startswith("Penicillin allergy")

        # DB: original AI output preserved verbatim on Finding columns.
        db_finding = Finding.objects.get(pk=fid)
        assert db_finding.summary == ai_summary
        assert db_finding.original_data["summary"] == ai_summary
        review = FindingReview.objects.get(finding=fid)
        assert review.decision == "edited"
        assert review.edited_status == "partially_omitted"

        # API: finding shows AI original distinctly from human edit.
        detail = self.client.get(f"/api/analyses/{analysis_id}/").data
        reviewed = next(f for f in detail["findings"] if f["id"] == fid)
        assert reviewed["summary"] == ai_summary  # AI original preserved
        assert reviewed["review"]["edited_summary"].startswith("Penicillin allergy")
        assert reviewed["review"]["edited_category"] == "allergy_or_adverse_reaction"

    def test_edit_accepts_documented_alias_fields(self):
        # The spec's conceptual payload uses summary/category/status; they must
        # map onto the stored edited_* fields.
        analysis_id, findings = self._create_and_get_findings()
        fid = findings[0]["id"]
        resp = self.client.post(
            f"/api/analyses/{analysis_id}/findings/{fid}/review/",
            {
                "decision": "edited",
                "summary": "Penicillin allergy (anaphylaxis) still omitted.",
                "category": "allergy_or_adverse_reaction",
                "status": "partially_omitted",
                "comment": "Clarified.",
            },
            format="json",
        )
        assert resp.status_code == 200, resp.data
        assert resp.data["edited_summary"].startswith("Penicillin allergy")
        assert resp.data["edited_category"] == "allergy_or_adverse_reaction"
        assert resp.data["edited_status"] == "partially_omitted"

    def test_review_summary_counts(self):
        analysis_id, findings = self._create_and_get_findings()
        assert len(findings) == 5

        self.client.post(
            f"/api/analyses/{analysis_id}/findings/{findings[0]['id']}/review/",
            {"decision": "accepted"}, format="json",
        )
        self.client.post(
            f"/api/analyses/{analysis_id}/findings/{findings[1]['id']}/review/",
            {"decision": "rejected"}, format="json",
        )
        self.client.post(
            f"/api/analyses/{analysis_id}/findings/{findings[2]['id']}/review/",
            {"decision": "edited", "edited_summary": "New wording."}, format="json",
        )
        resp = self.client.get(f"/api/analyses/{analysis_id}/review-summary/")
        assert resp.status_code == 200
        assert resp.data == {
            "total": 5,
            "accepted": 1,
            "rejected": 1,
            "edited": 1,
            "pending": 2,
        }

    def test_review_does_not_expose_original_finding_edit(self):
        # Re-reviewing a finding updates the decision, never the AI output.
        analysis_id, findings = self._create_and_get_findings()
        fid = findings[0]["id"]
        self.client.post(
            f"/api/analyses/{analysis_id}/findings/{fid}/review/",
            {"decision": "accepted"}, format="json",
        )
        self.client.post(
            f"/api/analyses/{analysis_id}/findings/{fid}/review/",
            {"decision": "rejected", "comment": "Reconsidered."}, format="json",
        )
        review = FindingReview.objects.get(finding_id=fid)
        assert review.decision == "rejected"
        assert Finding.objects.get(pk=fid).summary == Finding.objects.get(pk=fid).original_data["summary"]

    # ------------------------------------------------------------------
    # input validation + failure handling
    # ------------------------------------------------------------------
    def test_invalid_input_missing_handover(self):
        payload = default_payload()
        payload["handover"] = ""
        resp = self.client.post("/api/analyses/", payload, format="json")
        assert resp.status_code == 400
        assert "errors" in resp.data

    def test_invalid_mode(self):
        payload = default_payload()
        payload["mode"] = "oracle"
        resp = self.client.post("/api/analyses/", payload, format="json")
        assert resp.status_code == 400

    def test_invalid_profile_type(self):
        payload = default_payload()
        payload["patient_profile"] = ["not", "a", "dict"]
        resp = self.client.post("/api/analyses/", payload, format="json")
        assert resp.status_code == 400

    def test_empty_records_rejected(self):
        payload = default_payload()
        payload["records"] = []
        resp = self.client.post("/api/analyses/", payload, format="json")
        assert resp.status_code == 400

    def test_record_filename_cannot_be_ground_truth(self):
        payload = default_payload()
        payload["records"] = [
            {"filename": "ground_truth.json", "content": "{}"}
        ]
        resp = self.client.post("/api/analyses/", payload, format="json")
        assert resp.status_code == 400
        assert "ground_truth" in json.dumps(resp.data).lower()

    def test_record_content_cannot_contain_ground_truth(self):
        payload = default_payload()
        payload["records"] = [
            {"filename": "note.txt", "content": "the ground truth file contents"}
        ]
        resp = self.client.post("/api/analyses/", payload, format="json")
        assert resp.status_code == 400

    def test_reserved_filename_rejected(self):
        payload = default_payload()
        payload["records"] = [
            {"filename": "current_handover.txt", "content": "nope"}
        ]
        resp = self.client.post("/api/analyses/", payload, format="json")
        assert resp.status_code == 400

    def test_engine_failure_sets_failed_status(self):
        # Simulate a broken real-Gemini config (no key): the analysis must be
        # created with status="failed" and a useful, non-secret error message.
        with mock.patch.dict(
            os.environ,
            {"MH_EMITTER_BACKEND": "gemini", "GEMINI_API_KEY": ""},
            clear=False,
        ):
            resp = self.client.post(
                "/api/analyses/", default_payload("baseline"), format="json"
            )
        assert resp.status_code == 201
        assert resp.data["status"] == "failed"
        assert "GEMINI_API_KEY" in resp.data["error"]

    # ------------------------------------------------------------------
    # ground truth isolation guarantees
    # ------------------------------------------------------------------
    def test_inference_never_loads_ground_truth(self):
        with mock.patch(
            "medical_handover.eval.ground_truth.load_ground_truth",
            side_effect=AssertionError("ground truth loaded during inference"),
        ):
            for mode in ("baseline", "advanced"):
                with self.subTest(mode=mode):
                    resp = self.client.post(
                        "/api/analyses/", default_payload(mode), format="json"
                    )
                    assert resp.status_code == 201, resp.data
                    assert resp.data["status"] == "completed"

    def test_api_responses_never_contain_ground_truth(self):
        for mode in ("baseline", "advanced"):
            body = self.client.post(
                "/api/analyses/", default_payload(mode), format="json"
            ).data
            for endpoint in (
                f"/api/analyses/{body['id']}/",
                "/api/analyses/",
                f"/api/analyses/{body['id']}/review-summary/",
            ):
                got = self.client.get(endpoint)
                assert "ground_truth" not in json.dumps(got.data).lower(), endpoint
            if body["findings"]:
                fid = body["findings"][0]["id"]
                review = self.client.post(
                    f"/api/analyses/{body['id']}/findings/{fid}/review/",
                    {"decision": "accepted"}, format="json",
                )
                assert "ground_truth" not in json.dumps(review.data).lower()

    # ------------------------------------------------------------------
    # review input validation
    # ------------------------------------------------------------------
    def test_review_invalid_decision(self):
        analysis_id, findings = self._create_and_get_findings()
        resp = self.client.post(
            f"/api/analyses/{analysis_id}/findings/{findings[0]['id']}/review/",
            {"decision": "maybe"}, format="json",
        )
        assert resp.status_code == 400

    def test_edit_requires_edited_summary(self):
        analysis_id, findings = self._create_and_get_findings()
        resp = self.client.post(
            f"/api/analyses/{analysis_id}/findings/{findings[0]['id']}/review/",
            {"decision": "edited"}, format="json",
        )
        assert resp.status_code == 400
        assert "edited_summary" in resp.data["errors"]

    def test_edit_rejects_invalid_category_status_importance(self):
        analysis_id, findings = self._create_and_get_findings()
        fid = findings[0]["id"]
        base = f"/api/analyses/{analysis_id}/findings/{fid}/review/"
        for field in ("edited_category", "edited_status", "edited_importance"):
            with self.subTest(field=field):
                payload = {"decision": "edited", "edited_summary": "x.", field: "not-a-valid-value"}
                resp = self.client.post(base, payload, format="json")
                assert resp.status_code == 400, resp.data

    def test_review_not_found(self):
        analysis_id, _ = self._create_and_get_findings()
        resp = self.client.post(
            f"/api/analyses/{analysis_id}/findings/999999/review/",
            {"decision": "accepted"}, format="json",
        )
        assert resp.status_code == 404