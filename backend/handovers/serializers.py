"""Serializers for the handover analysis API.

Input serializers perform all user-input validation (including hard guards that
keep ground-truth concepts out of the engine and the API). Output serializers
preserve the original AI finding and present the human review separately.
"""

from __future__ import annotations

from rest_framework import serializers

from medical_handover.schema import (
    CATEGORIES,
    IMPORTANCE_LEVELS,
    STATUSES,
    canonical_category,
)

from .models import Analysis, Finding

# Never allow ground-truth concepts to enter through the API boundary, and never
# allow reserved engine filenames to be submitted as clinical records.
FORBIDDEN_TOKENS = ("ground_truth", "ground truth", "groundtruth")
RESERVED_RECORD_FILENAMES = ("current_handover.txt",)


def _check_forbidden_tokens(field_name: str, value: str) -> None:
    lowered = value.lower()
    for token in FORBIDDEN_TOKENS:
        if token in lowered:
            raise serializers.ValidationError(
                {field_name: f"{field_name} must not contain the forbidden token {token!r}."}
            )


class RecordItemSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255)
    content = serializers.CharField(allow_blank=False)

    def validate_filename(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("filename must not be empty.")
        lowered = name.lower()
        if lowered in RESERVED_RECORD_FILENAMES:
            raise serializers.ValidationError(
                f"'{name}' is a reserved filename and cannot be used as a record."
            )
        _check_forbidden_tokens("filename", name)
        return name

    def validate_content(self, value: str) -> str:
        _check_forbidden_tokens("content", value)
        return value


class AnalysisCreateSerializer(serializers.Serializer):
    """POST /api/analyses/ input validation."""

    patient_profile = serializers.JSONField()
    records = RecordItemSerializer(many=True, allow_empty=False)
    handover = serializers.CharField(allow_blank=False)
    mode = serializers.ChoiceField(choices=("baseline", "advanced"))

    def validate_patient_profile(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("patient_profile must be a JSON object.")
        return value

    def validate_handover(self, value: str) -> str:
        _check_forbidden_tokens("handover", value)
        return value


class FindingReviewSerializer(serializers.Serializer):
    """POST /api/analyses/{id}/findings/{finding_id}/review/ input validation."""

    decision = serializers.ChoiceField(choices=("accepted", "rejected", "edited"))
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    edited_summary = serializers.CharField(required=False, allow_blank=True, default="")
    edited_category = serializers.CharField(required=False, allow_blank=True, default="")
    edited_status = serializers.CharField(required=False, allow_blank=True, default="")
    edited_importance = serializers.CharField(required=False, allow_blank=True, default="")

    # Aliases matching the documented conceptual payload:
    # {"decision": "edited", "summary": "...", "category": "...", "status": "..."}
    summary = serializers.CharField(required=False, allow_blank=True, default="", write_only=True)
    category = serializers.CharField(required=False, allow_blank=True, default="", write_only=True)
    status = serializers.CharField(required=False, allow_blank=True, default="", write_only=True)
    importance = serializers.CharField(required=False, allow_blank=True, default="", write_only=True)

    def _merge_alias(self, attrs: dict, alias: str, target: str) -> None:
        if not str(attrs.get(target, "")).strip() and str(attrs.get(alias, "")).strip():
            attrs[target] = attrs[alias]

    def validate(self, attrs):
        for alias, target in (
            ("summary", "edited_summary"),
            ("category", "edited_category"),
            ("status", "edited_status"),
            ("importance", "edited_importance"),
        ):
            self._merge_alias(attrs, alias, target)

        decision = attrs.get("decision")

        if decision == "edited" and not str(attrs.get("edited_summary", "")).strip():
            raise serializers.ValidationError(
                {"edited_summary": "edited_summary is required when decision is 'edited'."}
            )

        category = str(attrs.get("edited_category", "")).strip()
        if category:
            canonical = canonical_category(category)
            if canonical not in CATEGORIES:
                raise serializers.ValidationError(
                    {"edited_category": f"Unknown category {category!r}. Allowed: {list(CATEGORIES)}."}
                )
            attrs["edited_category"] = canonical

        status = str(attrs.get("edited_status", "")).strip()
        if status and status not in STATUSES:
            raise serializers.ValidationError(
                {"edited_status": f"Unknown status {status!r}. Allowed: {list(STATUSES)}."}
            )

        importance = str(attrs.get("edited_importance", "")).strip()
        if importance and importance not in IMPORTANCE_LEVELS:
            raise serializers.ValidationError(
                {"edited_importance": f"Unknown importance {importance!r}. Allowed: {list(IMPORTANCE_LEVELS)}."}
            )

        return attrs


# ---------------------------------------------------------------------------
# Read-only output serializers
# ---------------------------------------------------------------------------
class ReviewSerializer(serializers.Serializer):
    decision = serializers.CharField()
    comment = serializers.CharField()
    edited_summary = serializers.CharField()
    edited_category = serializers.CharField()
    edited_importance = serializers.CharField()
    edited_status = serializers.CharField()
    reviewed_at = serializers.DateTimeField()


class FindingSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    order = serializers.IntegerField()
    # Flattened copy of the ORIGINAL AI output (never mutated by review).
    category = serializers.CharField()
    importance = serializers.CharField()
    status = serializers.CharField()
    summary = serializers.CharField()
    evidence_sources = serializers.ListField(child=serializers.CharField())

    original = serializers.SerializerMethodField()
    evidence = serializers.SerializerMethodField()
    review = serializers.SerializerMethodField()

    def get_original(self, obj) -> dict:
        return obj.original_data

    def get_evidence(self, obj) -> list[dict]:
        records_by_name = {r["filename"]: r["content"] for r in obj.analysis.records}
        out = []
        for name in obj.evidence_sources:
            content = records_by_name.get(name)
            if content is not None:
                out.append({"filename": name, "content": content})
        return out

    def get_review(self, obj):
        if not hasattr(obj, "review"):
            return None
        return ReviewSerializer(obj.review).data


def compute_review_summary(analysis: Analysis) -> dict:
    total = analysis.findings.count()
    counts = {"accepted": 0, "rejected": 0, "edited": 0}
    for finding in analysis.findings.all():
        try:
            review = finding.review
        except Finding.review.RelatedObjectDoesNotExist:
            continue
        if review.decision in counts:
            counts[review.decision] += 1
    decided = counts["accepted"] + counts["rejected"] + counts["edited"]
    return {
        "total": total,
        "accepted": counts["accepted"],
        "rejected": counts["rejected"],
        "edited": counts["edited"],
        "pending": total - decided,
    }


class AnalysisDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    mode = serializers.CharField()
    status = serializers.CharField()
    patient_profile = serializers.JSONField()
    records = serializers.JSONField()
    handover = serializers.CharField()
    engine_meta = serializers.JSONField()
    error = serializers.CharField()
    findings = serializers.SerializerMethodField()
    review_summary = serializers.SerializerMethodField()

    def get_findings(self, obj):
        return FindingSerializer(obj.findings.all(), many=True).data

    def get_review_summary(self, obj):
        return compute_review_summary(obj)


class AnalysisListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    mode = serializers.CharField()
    status = serializers.CharField()
    finding_count = serializers.SerializerMethodField()
    review_summary = serializers.SerializerMethodField()

    def get_finding_count(self, obj) -> int:
        return obj.findings.count()

    def get_review_summary(self, obj):
        return compute_review_summary(obj)