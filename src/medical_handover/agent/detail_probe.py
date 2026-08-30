"""Stage 4 — DETAIL probe (one targeted LLM call per case).

Targets the measured recall gaps where the one-shot baseline caught a category
but missed the fine-grained detail: exact numeric targets (e.g. BP 120-140),
medication restrictions (e.g. 'no anticoagulants without approval'), and explicit
escalation criteria. This is a second, narrowly-scoped pass over ALL records
focused only on those detail types, appended to the verified candidates.
"""

from __future__ import annotations

from ..baseline import RECORD_BEGIN, RECORD_END, findings_from_payload
from ..models import Case
from ..schema import CATEGORIES
from .prompt_guard import assert_no_gt


_DETAIL_SYSTEM = (
    "You are a detail-focused reviewer for a clinical handover-quality check. "
    "Given the full clinical record set and the current handover, identify ONLY "
    "specific, fine-grained clinical details that are present in the records but "
    "clearly MISSING (not merely vague) from the handover. Focus strictly on:\n"
    "  - EXACT numeric targets (e.g. blood-pressure target 120-140 mmHg, SpO2 "
    "target, glucose target)\n"
    "  - explicit MEDICATION RESTRICTIONS (e.g. 'no anticoagulants without "
    "approval', allergy-based prohibitions)\n"
    "  - explicit ESCALATION CRITERIA (e.g. 'call registrar if GCS drops', "
    "'repeat ECG and escalate if chest pain recurs')\n"
    "Hard rules to avoid false positives:\n"
    "  - Do NOT emit a detail if the handover already states it (even in other "
    "words). Verify absence in the handover before emitting.\n"
    "  - Do NOT repeat the same category/item the handover already covers.\n"
    "  - Do NOT invent information absent from the records.\n"
    "  - Prefer HIGH confidence, specific, actionable details only.\n"
    "Respond ONLY with strict JSON:\n"
    "{\"findings\": [{\"category\": <canonical>, \"importance\": "
    "\"critical\"|\"high\"|\"medium\"|\"low\", \"status\": "
    "\"omitted\"|\"partially_omitted\", \"summary\": <str>, \"evidence_sources\": "
    "[<exact record filename>]}]}\n"
    "Canonical categories: " + ", ".join(CATEGORIES) + "\n"
)


def build_detail_prompt(case: Case) -> str:
    lines: list[str] = [_DETAIL_SYSTEM, ""]
    for rec in case.records:
        if rec.filename == "current_handover.txt":
            continue
        lines.append(f"{RECORD_BEGIN}{rec.filename}>>>")
        lines.append(rec.text.strip())
        lines.append(RECORD_END)
        lines.append("")
    lines.append("CURRENT HANDOVER:")
    lines.append(case.handover.text.strip())
    return "\n".join(lines)


def probe_details(case: Case, client) -> tuple:
    prompt = build_detail_prompt(case)
    assert_no_gt(prompt)
    try:
        payload = client.complete_json(prompt)
    except Exception:
        return ()
    return findings_from_payload(payload)
