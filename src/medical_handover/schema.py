from __future__ import annotations

from enum import Enum


class Category(str, Enum):
    """Canonical finding categories exposed to the model and used by the scorer.

    The benchmark's ground-truth data uses several raw/aliased spellings
    (e.g. ``monitoring_target`` vs ``monitoring``). The model is instructed to
    emit only these canonical values; ``canonical_category`` folds both the raw
    and aliased spellings back onto the same canonical string so that model
    vocabulary and scoring agree.
    """

    ALLERGY = "allergy_or_adverse_reaction"
    CLINICAL_STATUS = "clinical_status"
    ESCALATION = "escalation"
    MEDICATION = "medication"
    MONITORING = "monitoring"
    PENDING_CONSULT = "pending_consult"
    PENDING_INVESTIGATION = "pending_investigation"
    PENDING_RESULT = "pending_result"
    PROCEDURE = "procedure"
    SAFETY = "safety"


CATEGORIES: tuple[str, ...] = tuple(c.value for c in Category)


STATUSES: tuple[str, ...] = ("omitted", "partially_omitted")


IMPORTANCE_LEVELS: tuple[str, ...] = ("critical", "high", "medium", "low")


# Raw/aliased category spelling -> canonical category. Includes identity entries
# so that canonical_category is idempotent and the scorer can normalize both
# predicted and ground-truth categories through one map.
CATEGORY_ALIASES: dict[str, str] = {
    "allergy": "allergy_or_adverse_reaction",
    "allergy_or_adverse_reaction": "allergy_or_adverse_reaction",
    "clinical_status": "clinical_status",
    "recent_deterioration": "clinical_status",
    "recent_event": "clinical_status",
    "escalation": "escalation",
    "medication": "medication",
    "medication_safety": "medication",
    "monitoring": "monitoring",
    "monitoring_target": "monitoring",
    "pending_consult": "pending_consult",
    "pending_investigation": "pending_investigation",
    "pending_result": "pending_result",
    "procedure": "procedure",
    "safety": "safety",
    "mobility_safety": "safety",
}


def canonical_category(category: str) -> str:
    """Fold a raw or aliased category spelling onto its canonical form."""
    return CATEGORY_ALIASES.get(category, category)


def is_valid_category(category: str) -> bool:
    return canonical_category(category) in CATEGORIES


def is_valid_status(status: str) -> bool:
    return status in STATUSES
