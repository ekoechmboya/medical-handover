from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class ClinicalRecord:
    filename: str
    text: str
    timestamp: datetime | None = None
    date_only: date | None = None
    year_only: int | None = None

    @property
    def effective_time(self) -> datetime | None:
        if self.timestamp is not None:
            return self.timestamp
        if self.date_only is not None:
            return datetime.combine(self.date_only, datetime.min.time())
        if self.year_only is not None:
            return datetime(self.year_only, 1, 1)
        return None


@dataclass(frozen=True)
class Case:
    case_id: str
    title: str
    difficulty: str
    patient_id: str
    age: int
    sex: str
    admission_reason: str
    current_location: str
    directory: Path
    handover: ClinicalRecord
    records: tuple[ClinicalRecord, ...] = field(default=())

    @property
    def timeline(self) -> tuple[ClinicalRecord, ...]:
        return tuple(
            sorted(
                self.records,
                key=lambda r: (r.effective_time is None, r.effective_time or datetime.max, r.filename),
            )
        )


@dataclass(frozen=True)
class Finding:
    category: str
    importance: str
    status: str
    summary: str
    evidence_sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class GroundTruthFinding:
    finding_id: str
    category: str
    importance: str
    status: str
    expected_text: str
    evidence_sources: tuple[str, ...]


@dataclass(frozen=True)
class GroundTruth:
    case_id: str
    expected_findings: tuple[GroundTruthFinding, ...]
    negative_findings: tuple[str, ...]