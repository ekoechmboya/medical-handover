"""Advanced handover-quality agent package.

Stages (cumulative ablation):
  generate   -> one-shot baseline call (unchanged prompt)        [baseline_emit]
  verify     -> semantic VERIFY of each candidate (1 LLM call)    [agent.verify]
  detail     -> targeted DETAIL probe for targets/restrictions/escalation (1 LLM call)
  reconcile  -> rule-based status + canonical category            [agent.reconcile]
  dedup      -> rule-based redundancy pruning                     [agent.dedup]

Every agent prompt passes through `prompt_guard.assert_no_gt`. Ground truth is
only consumed downstream by the scorer, never inside the agent.
"""

from .detail_probe import probe_details
from .dedup import dedup
from .pipeline import (
    PipelineResult,
    STAGE_DEDUP,
    STAGE_DETAIL,
    STAGE_RECONCILE,
    STAGE_VERIFY,
    run_pipeline,
)
from .prompt_guard import assert_no_gt
from .reconcile import reconcile
from .retrieve import retrieve_evidence
from .verify import verify_batch

__all__ = [
    "run_pipeline",
    "PipelineResult",
    "verify_batch",
    "probe_details",
    "reconcile",
    "dedup",
    "retrieve_evidence",
    "assert_no_gt",
    "STAGE_VERIFY",
    "STAGE_DETAIL",
    "STAGE_RECONCILE",
    "STAGE_DEDUP",
]
