"""Database models for handover analyses and human review.

The AI output is a set of *candidate* findings; nothing here is ever treated as
an executed clinical action. Human review decisions are stored separately from
the original AI finding (see ``Finding.original_data`` vs ``FindingReview``).
"""

from django.db import models

MODE_CHOICES = (
    ("baseline", "baseline"),
    ("advanced", "advanced"),
)

ANALYSIS_STATUS_CHOICES = (
    ("pending", "pending"),
    ("running", "running"),
    ("completed", "completed"),
    ("failed", "failed"),
)

REVIEW_DECISION_CHOICES = (
    ("accepted", "accepted"),
    ("rejected", "rejected"),
    ("edited", "edited"),
)


class Analysis(models.Model):
    """A single analysis run: submitted inputs + any engine metadata."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    mode = models.CharField(max_length=16, choices=MODE_CHOICES)
    status = models.CharField(
        max_length=16, choices=ANALYSIS_STATUS_CHOICES, default="pending"
    )

    patient_profile = models.JSONField(default=dict)
    records = models.JSONField(default=list)  # [{"filename": str, "content": str}]
    handover = models.TextField()

    # Observability only: stage timing/token logs from the engine when present.
    engine_meta = models.JSONField(default=dict, blank=True)

    # Human-readable failure when status == "failed".
    error = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"Analysis #{self.pk} (mode={self.mode}, status={self.status})"


class Finding(models.Model):
    """One candidate finding produced by the engine.

    ``original_data`` permanently preserves the raw AI finding dict. The
    flattened fields are convenience copies of that same AI output and are never
    mutated by human review edits (those live on ``FindingReview``).
    """

    analysis = models.ForeignKey(
        Analysis, on_delete=models.CASCADE, related_name="findings"
    )
    order = models.PositiveIntegerField(default=0)

    category = models.CharField(max_length=64)
    importance = models.CharField(max_length=16)
    status = models.CharField(max_length=32)
    summary = models.TextField()
    evidence_sources = models.JSONField(default=list, blank=True)

    original_data = models.JSONField(default=dict)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"Finding #{self.pk} [{self.category}] {self.summary[:60]}"


class FindingReview(models.Model):
    """Human review decision for a single finding.

    Stored separately from the AI output so the original finding is always
    preserved. ``edited_*`` fields only carry meaning when decision == "edited".
    """

    finding = models.OneToOneField(
        Finding, on_delete=models.CASCADE, related_name="review"
    )
    decision = models.CharField(max_length=16, choices=REVIEW_DECISION_CHOICES)
    comment = models.TextField(blank=True, default="")

    edited_summary = models.TextField(blank=True, default="")
    edited_category = models.CharField(max_length=64, blank=True, default="")
    edited_importance = models.CharField(max_length=16, blank=True, default="")
    edited_status = models.CharField(max_length=32, blank=True, default="")

    reviewed_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Review({self.decision}) for Finding #{self.finding_id}"