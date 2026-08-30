from __future__ import annotations

import json

from .llm import (
    HANDOVER_BEGIN,
    HANDOVER_END,
    PROFILE_BEGIN,
    PROFILE_END,
    RECORD_BEGIN,
    RECORD_END,
    get_client,
)
from .models import Case, Finding
from .schema import canonical_category, is_valid_status

_SYSTEM = (
    "You are a clinical handover-quality reviewer. Given a patient profile, the "
    "clinical records available at the time of handover, and the current "
    "handover note, identify information that is CLINICALLY IMPORTANT but "
    "MISSING or only PARTIALLY present in the handover (i.e. omissions a "
    "receiving clinician would need). Do NOT invent information that is absent "
    "from the records. Respond ONLY with strict JSON.\n\n"
    "Use exactly this schema:\n"
    "{\n"
    '  "findings": [\n'
    "    {\n"
    '      "category": <one of the canonical categories below>,\n'
    '      "importance": "critical" | "high" | "medium" | "low",\n'
    '      "status": "omitted" | "partially_omitted",\n'
    '      "summary": "concise statement of the omitted item",\n'
    '      "evidence_sources": ["exact filename of the record(s) that support this, e.g. progress_note.txt"]\n'
    "    }\n"
    "  ]\n"
    "}\n\n"
    "Canonical categories (use these exact strings):\n"
    "<<CATEGORIES>>\n\n"
    "Rules:\n"
    "- status is 'omitted' if the item is absent from the handover, "
    "'partially_omitted' if present but incomplete.\n"
    "- evidence_sources MUST be exact filenames from the records you were given.\n"
    "- Only emit findings supported by the provided records.\n"
)


def build_prompt(case: Case) -> str:
    """Construct the model prompt from allowed inputs only (never ground truth)."""
    lines: list[str] = [_SYSTEM.replace("<<CATEGORIES>>", ", ".join(_canonical_categories()))]

    lines.append(PROFILE_BEGIN)
    lines.append(
        json.dumps(
            {
                "case_id": case.case_id,
                "title": case.title,
                "difficulty": case.difficulty,
                "patient_id": case.patient_id,
                "age": case.age,
                "sex": case.sex,
                "admission_reason": case.admission_reason,
                "current_location": case.current_location,
            },
            indent=2,
        )
    )
    lines.append(PROFILE_END)

    for record in case.records:
        lines.append(f"{RECORD_BEGIN}{record.filename}>>>")
        lines.append(record.text.strip())
        lines.append(RECORD_END)

    lines.append(HANDOVER_BEGIN)
    lines.append(case.handover.text.strip())
    lines.append(HANDOVER_END)

    return "\n".join(lines)


def _canonical_categories() -> list[str]:
    from .schema import CATEGORIES

    return list(CATEGORIES)


def findings_from_payload(payload: object) -> tuple[Finding, ...]:
    """Parse a model JSON payload into canonical Finding tuples.

    The prompt is built strictly from the patient profile, the allowed .txt
    records, and the current handover. Ground truth is never read or passed in.
    """
    raw_findings = payload.get("findings", []) if isinstance(payload, dict) else []

    findings: list[Finding] = []
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        category = canonical_category(str(item.get("category", "")))
        status = str(item.get("status", "omitted"))
        if not is_valid_status(status):
            status = "omitted"
        evidence = tuple(str(s) for s in item.get("evidence_sources", []))
        findings.append(
            Finding(
                category=category,
                importance=str(item.get("importance", "high")),
                status=status,
                summary=str(item.get("summary", "")).strip(),
                evidence_sources=evidence,
            )
        )
    return tuple(findings)


def baseline_emit(case: Case, client=None) -> tuple[Finding, ...]:
    """Non-agentic baseline: one LLM call, parse JSON into Findings.

    The prompt is built strictly from the patient profile, the allowed .txt
    records, and the current handover. Ground truth is never read or passed in.
    """
    if client is None:
        client = get_client()

    prompt = build_prompt(case)
    payload = client.complete_json(prompt)
    return findings_from_payload(payload)
