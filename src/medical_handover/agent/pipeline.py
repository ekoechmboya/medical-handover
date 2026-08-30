"""Agent pipeline orchestration for the ablation study.

`run_pipeline` executes the candidate stages in a fixed order and returns the
final findings plus, for every enabled stage, the intermediate findings and a
structured change log (so we can later attribute improvements to specific
stages). It never touches ground truth: scoring happens in the runner only.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from ..baseline import baseline_emit
from ..models import Case, Finding
from .detail_probe import probe_details
from .dedup import dedup
from .reconcile import reconcile
from .verify import verify_batch


# Canonical stage flags used by the ablation configs.
STAGE_VERIFY = "verify"
STAGE_DETAIL = "detail"
STAGE_RECONCILE = "reconcile"
STAGE_DEDUP = "dedup"


def _usage_dict(client) -> dict | None:
    um = getattr(client, "last_usage_metadata", None)
    if um is None:
        return None
    return {
        "prompt_token_count": getattr(um, "prompt_token_count", None),
        "candidates_token_count": getattr(um, "candidates_token_count", None),
        "total_token_count": getattr(um, "total_token_count", None),
    }


def _fdict(f: Finding) -> dict:
    return {
        "category": f.category,
        "importance": f.importance,
        "status": f.status,
        "summary": f.summary,
        "evidence_sources": list(f.evidence_sources),
    }


@dataclass
class PipelineResult:
    final: tuple[Finding, ...] = ()
    intermediates: dict[str, list[dict]] = field(default_factory=dict)
    logs: dict = field(default_factory=dict)
    timing: dict = field(default_factory=dict)
    tokens: dict = field(default_factory=dict)


def run_pipeline(
    case: Case, client, enabled: set[str] | None = None
) -> PipelineResult:
    enabled = enabled or set()
    res = PipelineResult()

    # --- Stage 1: GENERATE (reuses the exact one-shot baseline call). ---
    t0 = time.perf_counter()
    candidates = baseline_emit(case, client)
    res.timing["generate"] = round(time.perf_counter() - t0, 3)
    res.tokens["generate"] = _usage_dict(client)
    res.intermediates["generate"] = [_fdict(f) for f in candidates]

    current: list[Finding] = list(candidates)
    semantic: dict[int, str] = {}  # position-in-current -> Stage 3 semantic status

    # --- Stage 3: VERIFY (batched LLM call). ---
    if STAGE_VERIFY in enabled:
        t0 = time.perf_counter()
        vr = verify_batch(case, tuple(current), client)
        res.timing[STAGE_VERIFY] = round(time.perf_counter() - t0, 3)
        res.tokens[STAGE_VERIFY] = _usage_dict(client)

        kept_current: list[Finding] = []
        sem_pos: dict[int, str] = {}
        for d in vr.decisions:
            if d.kept and d.finding is not None:
                sem_pos[len(kept_current)] = d.finding.status
                kept_current.append(d.finding)
        semantic = sem_pos
        current = kept_current
        res.intermediates[STAGE_VERIFY] = [_fdict(f) for f in current]
        res.logs[STAGE_VERIFY] = {
            "before": [_fdict(f) for f in candidates],
            "after": [_fdict(f) for f in current],
            "removed": list(vr.removed),
        }

    # --- Stage 4: DETAIL (targeted LLM call). ---
    if STAGE_DETAIL in enabled:
        t0 = time.perf_counter()
        extra = probe_details(case, client)
        res.timing[STAGE_DETAIL] = round(time.perf_counter() - t0, 3)
        res.tokens[STAGE_DETAIL] = _usage_dict(client)
        # Detail findings are NOT semantically verified in this design; they enter
        # reconcile/dedup unverified.
        current = current + list(extra)
        res.intermediates[STAGE_DETAIL] = [_fdict(f) for f in current]
        res.logs[STAGE_DETAIL] = {"added": [_fdict(f) for f in extra]}

    # --- Stage 5: RECONCILE (rule-based status + category). ---
    if STAGE_RECONCILE in enabled:
        t0 = time.perf_counter()
        rr = reconcile(tuple(current), case, semantic=semantic)
        res.timing[STAGE_RECONCILE] = round(time.perf_counter() - t0, 3)
        res.tokens[STAGE_RECONCILE] = None
        current = list(rr.findings)
        res.intermediates[STAGE_RECONCILE] = [_fdict(f) for f in current]
        res.logs[STAGE_RECONCILE] = {"status_changes": list(rr.changes)}

    # --- Stage 6: DEDUP (rule-based). ---
    if STAGE_DEDUP in enabled:
        t0 = time.perf_counter()
        dr = dedup(tuple(current))
        res.timing[STAGE_DEDUP] = round(time.perf_counter() - t0, 3)
        res.tokens[STAGE_DEDUP] = None
        current = list(dr.findings)
        res.intermediates[STAGE_DEDUP] = [_fdict(f) for f in current]
        res.logs[STAGE_DEDUP] = {"removed": list(dr.removed)}

    res.final = tuple(current)
    return res
