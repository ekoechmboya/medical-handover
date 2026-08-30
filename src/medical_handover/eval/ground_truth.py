from __future__ import annotations

import json
from pathlib import Path

from ..models import GroundTruth, GroundTruthFinding


def load_ground_truth(case_dir: Path, case_id: str) -> GroundTruth:
    gt_path = case_dir / "ground_truth.json"
    if not gt_path.is_file():
        raise FileNotFoundError(f"Missing ground_truth.json for {case_id}")
    data = json.loads(gt_path.read_text(encoding="utf-8"))

    findings = tuple(
        GroundTruthFinding(
            finding_id=str(f.get("finding_id", "finding_" + str(idx))),
            category=str(f["category"]),
            importance=str(f["importance"]),
            status=str(f["status"]),
            expected_text=str(f["expected_text"]),
            evidence_sources=tuple(str(s) for s in f.get("evidence_sources", [])),
        )
        for idx, f in enumerate(data.get("expected_findings", []))
    )
    negatives = tuple(str(n) for n in data.get("negative_findings", []))
    return GroundTruth(case_id=case_id, expected_findings=findings, negative_findings=negatives)