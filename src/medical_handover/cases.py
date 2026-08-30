from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

from .models import Case, ClinicalRecord

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_HANDOVER_FILENAME = "current_handover.txt"
_HEADER_TIME_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})\b")
_DATE_ONLY_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b(?!\s+(?:at\s+)?\d{1,2}:\d{2})")
_YEAR_ONLY_RE = re.compile(r"\b(19\d{2}|20\d{2})\b(?!-\d{2})")
_REQUIRED_PROFILE_FIELDS = (
    "case_id", "title", "difficulty", "patient_id",
    "age", "sex", "admission_reason", "current_location",
)


def find_data_roots(project_root: Path = PROJECT_ROOT) -> list[Path]:
    """Locate benchmark data roots (sibling folders carrying data/benchmark_manifest.json)."""
    roots = sorted(
        (p for p in project_root.iterdir() if (p / "data" / "benchmark_manifest.json").is_file()),
        key=str,
    )
    if not roots:
        raise FileNotFoundError(f"No benchmark data roots found under {project_root}")
    return roots


def load_cases(roots: list[Path] | None = None) -> list[Case]:
    roots = [root / "data" for root in find_data_roots()] if roots is None else roots
    cases: list[Case] = []
    for root in roots:
        manifest_path = Path(root) / "benchmark_manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"No benchmark manifest found at {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest["cases"]:
            case = load_case(Path(root) / "cases" / str(entry["case_id"]))
            if any(c.case_id == case.case_id for c in cases):
                raise ValueError(f"Duplicate case_id across data roots: {case.case_id}")
            cases.append(case)
    cases.sort(key=lambda c: c.case_id)
    return cases


def load_case(case_dir: Path) -> Case:
    if not case_dir.is_dir():
        raise FileNotFoundError(f"Case directory not found: {case_dir}")
    profile_path = case_dir / "patient_profile.json"
    if not profile_path.is_file():
        raise FileNotFoundError(f"Missing patient_profile.json in {case_dir}")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    for key in _REQUIRED_PROFILE_FIELDS:
        if key not in profile:
            raise ValueError(f"{case_dir.name}: patient_profile.json is missing field {key!r}")

    handover = _load_record(case_dir / _HANDOVER_FILENAME, required=True)

    records: list[ClinicalRecord] = []
    for path in sorted(case_dir.glob("*.txt")):
        if path.name == _HANDOVER_FILENAME:
            continue
        records.append(_load_record(path, required=True))

    return Case(
        case_id=str(profile["case_id"]),
        title=str(profile["title"]),
        difficulty=str(profile["difficulty"]),
        patient_id=str(profile["patient_id"]),
        age=int(profile["age"]),
        sex=str(profile["sex"]),
        admission_reason=str(profile["admission_reason"]),
        current_location=str(profile["current_location"]),
        directory=case_dir,
        handover=handover,
        records=tuple(records),
    )


def _load_record(path: Path, *, required: bool) -> ClinicalRecord:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required file: {path}")
        raise FileNotFoundError(f"Missing record file: {path}")
    text = path.read_text(encoding="utf-8")
    header = "\n".join(text.splitlines()[:2])
    timestamp = parse_timestamp(header)
    date_only = None if timestamp is not None else parse_date_only(header)
    year_only = None if timestamp is not None or date_only is not None else parse_year_only(header)
    return ClinicalRecord(
        filename=path.name,
        text=text,
        timestamp=timestamp,
        date_only=date_only,
        year_only=year_only,
    )


def parse_timestamp(text: str) -> datetime | None:
    match = _HEADER_TIME_RE.search(text)
    if match is None:
        return None
    return datetime(*[int(g) for g in match.groups()])


def parse_date_only(text: str) -> date | None:
    match = _DATE_ONLY_RE.search(text)
    if match is None:
        return None
    return date(*[int(g) for g in match.groups()])


def parse_year_only(text: str) -> int | None:
    match = _YEAR_ONLY_RE.search(text)
    if match is None:
        return None
    return int(match.group(1))


def validate_case(case: Case) -> list[str]:
    problems: list[str] = []
    if case.handover.timestamp is None:
        problems.append(f"{case.case_id}: handover has no header timestamp")
    if not case.records:
        problems.append(f"{case.case_id}: no clinical records found")
    if case.handover.timestamp is not None:
        for record in case.records:
            effective = record.effective_time
            if effective is not None and effective > case.handover.timestamp:
                problems.append(
                    f"{case.case_id}: record {record.filename} is dated after the handover "
                    f"({effective.isoformat()})"
                )
    return problems


def undated_records(case: Case) -> list[ClinicalRecord]:
    return [r for r in case.records if r.effective_time is None]