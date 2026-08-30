"""Leakage guard for all agent prompts.

Every prompt built inside the agent package MUST pass through `assert_no_gt`
before being sent to the model. The agent is only ever allowed to see the
patient profile, the allowed clinical records, the current handover, and its own
intermediate findings. Ground truth is never constructed into a prompt and is
only consumed by the scorer after all findings are produced.
"""

from __future__ import annotations

import re

# Substrings that must never appear in an agent prompt. The ground-truth file is
# always named exactly "ground_truth.json" inside each case directory, so its
# presence (or the concept) is a hard signal of leakage.
_FORBIDDEN = ("ground_truth", "ground truth", "groundtruth")


def assert_no_gt(prompt: str) -> None:
    """Raise ValueError if the prompt could leak ground truth.

    This is a defensive, best-effort guard. It is intentionally strict: any
    mention of the ground-truth concept aborts the call rather than risk
    contaminating the evaluation.
    """
    lowered = prompt.lower()
    for token in _FORBIDDEN:
        if token in lowered:
            raise ValueError(
                f"GT leak guard tripped: prompt contains forbidden token {token!r}. "
                "Agent prompts must only use profile/records/handover/findings."
            )
    # Also forbid the literal canonical ground-truth filename.
    if re.search(r"ground_truth\.json", prompt):
        raise ValueError(
            "GT leak guard tripped: prompt references ground_truth.json. "
            "Agent prompts must never name the ground-truth file."
        )
