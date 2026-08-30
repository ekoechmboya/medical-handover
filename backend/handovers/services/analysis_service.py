"""Analysis service: wraps the existing engine (no engine logic is duplicated).

The Django layer only adapts the submitted patient_profile/records/handover into
the engine's ``Case`` shape, selects an LLM client from ``MH_EMITTER_BACKEND``,
and delegates to either:

  * ``medical_handover.baseline.baseline_emit``   (one-shot baseline), or
  * ``medical_handover.agent.run_pipeline``       (advanced agentic pipeline)

Ground truth is never loaded here, never passed to the engine, and never
exposed through the API (see tests).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from medical_handover.agent import (
    STAGE_DEDUP,
    STAGE_DETAIL,
    STAGE_RECONCILE,
    STAGE_VERIFY,
    run_pipeline,
)
from medical_handover.baseline import baseline_emit
from medical_handover.cases import (
    parse_date_only,
    parse_timestamp,
    parse_year_only,
)
from medical_handover.llm import get_client
from medical_handover.models import Case, ClinicalRecord

from ..models import Analysis, Finding

# Advanced mode = the full cumulative ablation configuration (B+V+D+R+De).
ADVANCED_STAGES = frozenset(
    {STAGE_VERIFY, STAGE_DETAIL, STAGE_RECONCILE, STAGE_DEDUP}
)

FORBIDDEN_PATTERNS = ("ground_truth", "ground truth", "groundtruth")


class QuotaSafeClient:
    """Pace + retry wrapper for the real Gemini backend.

    Mirrors the minimal behaviour of ``run_agent.RateLimitedClient`` so free-tier
    quota (~20 req/min) is not burst through. The offline MockClient runs without
    this wrapper. This is client plumbing only; it does not re-implement agent
    logic.
    """

    def __init__(self, client, min_spacing_s: float = 5.0, max_retries: int = 4):
        self._client = client
        self._min_spacing = min_spacing_s
        self._max_retries = max_retries
        self._last = 0.0

    @property
    def last_usage_metadata(self):
        return getattr(self._client, "last_usage_metadata", None)

    def complete_json(self, prompt: str) -> dict:
        for attempt in range(self._max_retries):
            now = time.perf_counter()
            wait = self._min_spacing - (now - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                out = self._client.complete_json(prompt)
                self._last = time.perf_counter()
                return out
            except Exception as exc:  # noqa: BLE001
                msg = f"{type(exc).__name__}: {exc}"
                transient = any(
                    s in msg
                    for s in (
                        "ResourceExhausted",
                        "429",
                        "503",
                        "504",
                        "UNAVAILABLE",
                        "DEADLINE_EXCEEDED",
                        "timed out",
                        "Timeout",
                    )
                )
                if transient:
                    time.sleep(20 + attempt * 15)
                    continue
                raise
        raise RuntimeError("QuotaSafeClient: exhausted retries on Gemini call")


def emitter_backend() -> str:
    return os.environ.get("MH_EMITTER_BACKEND", "mock")


def build_client():
    """Select the engine client. Offline by default; Gemini when configured."""
    backend = emitter_backend()
    client = get_client(backend=backend, temperature=0.0)
    if backend == "gemini":
        client = QuotaSafeClient(client)
    return client


def _as_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_case(analysis: Analysis) -> Case:
    """Adapt submitted inputs into the engine's Case shape.

    The engine only needs profile fields, record text, and the handover text
    during inference; timestamps are parsed from record headers for nicer
    ordering but are not required.
    """
    profile = analysis.patient_profile or {}

    records: list[ClinicalRecord] = []
    for item in analysis.records or []:
        text = str(item.get("content", ""))
        header = "\n".join(text.splitlines()[:2])
        timestamp = parse_timestamp(header)
        records.append(
            ClinicalRecord(
                filename=str(item.get("filename", "")),
                text=text,
                timestamp=timestamp,
                date_only=None
                if timestamp is not None
                else parse_date_only(header),
                year_only=None
                if timestamp is not None or parse_date_only(header) is not None
                else parse_year_only(header),
            )
        )

    handover = ClinicalRecord(
        filename="current_handover.txt",
        text=analysis.handover,
    )

    return Case(
        case_id=str(profile.get("case_id") or "demo"),
        title=str(profile.get("title") or "Demo handover case"),
        difficulty=str(profile.get("difficulty") or "demo"),
        patient_id=str(profile.get("patient_id") or "demo"),
        age=_as_int(profile.get("age")),
        sex=str(profile.get("sex") or ""),
        admission_reason=str(profile.get("admission_reason") or ""),
        current_location=str(profile.get("current_location") or ""),
        directory=Path("."),
        handover=handover,
        records=tuple(records),
    )


def _finding_to_dict(finding) -> dict:
    return {
        "category": finding.category,
        "importance": finding.importance,
        "status": finding.status,
        "summary": finding.summary,
        "evidence_sources": list(finding.evidence_sources),
    }


def _persist_findings(analysis: Analysis, findings) -> None:
    Finding.objects.filter(analysis=analysis).delete()
    for order, finding in enumerate(findings):
        original = _finding_to_dict(finding)
        Finding.objects.create(
            analysis=analysis,
            order=order,
            category=finding.category,
            importance=finding.importance,
            status=finding.status,
            summary=finding.summary,
            evidence_sources=list(finding.evidence_sources),
            original_data=original,
        )


def run_analysis(analysis: Analysis) -> None:
    """Run the engine for `analysis` and persist findings/status.

    Synchronous by design for this milestone. Any engine failure leaves the
    analysis with status="failed" and a useful `error` message instead of
    crashing the request.
    """
    try:
        case = build_case(analysis)
        client = build_client()

        if analysis.mode == "baseline":
            findings = baseline_emit(case, client)
            meta = {
                "backend": emitter_backend(),
                "stages": ["generate"],
            }
        else:
            result = run_pipeline(case, client, enabled=set(ADVANCED_STAGES))
            findings = result.final
            meta = {
                "backend": emitter_backend(),
                "stages": ["generate", "verify", "detail", "reconcile", "dedup"],
                "timing_s": result.timing,
                "tokens": result.tokens,
                "logs": result.logs,
            }

        _persist_findings(analysis, findings)
        analysis.engine_meta = meta
        analysis.error = ""
        analysis.status = "completed"
    except Exception as exc:  # noqa: BLE001
        analysis.engine_meta = {"backend": emitter_backend()}
        analysis.error = f"{type(exc).__name__}: {exc}"
        analysis.status = "failed"
    analysis.save()
    analysis.refresh_from_db()
    return analysis