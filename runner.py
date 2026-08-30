"""CLI to evaluate an emitter against the synthetic benchmark.

Usage:
  python runner.py --emitter oracle --all
  python runner.py --emitter null --all
  python runner.py --emitter oracle --cases case_01 case_07

Ground truth files are opened only during the scoring phase and are never
passed to an emitter. The oracle emitter is the single documented exception,
for scorer calibration only.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from medical_handover.baseline import baseline_emit  # noqa: E402
from medical_handover.cases import load_cases  # noqa: E402
from medical_handover.eval.ground_truth import load_ground_truth  # noqa: E402
from medical_handover.eval.probes import null_emit, oracle_emit  # noqa: E402
from medical_handover.eval.report import export_to_json, format_case_table, format_summary  # noqa: E402
from medical_handover.eval.scorer import score_case  # noqa: E402

EMITTERS = {
    "baseline": baseline_emit,
    "oracle": oracle_emit,
    "null": null_emit,
}

# Oracle replays ground truth verbatim: it is a calibration/upper-bound probe
# only, never a real system under test. It must be opted into explicitly.
CALIBRATION_ONLY = {"oracle"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate a handover-quality emitter against the benchmark.")
    parser.add_argument("--emitter", choices=sorted(EMITTERS), required=True, help="Emitter to evaluate")
    parser.add_argument("--cases", nargs="*", default=None, help="Case ids to run")
    parser.add_argument("--all", action="store_true", help="Run every case")
    parser.add_argument(
        "--calibration",
        action="store_true",
        help="Required to run calibration-only emitters (e.g. oracle). These replay "
        "ground truth and must NEVER be used to evaluate a real system.",
    )
    parser.add_argument("--export-dir", default=Path(ROOT) / "reports")
    args = parser.parse_args(argv)

    if not args.all and not args.cases:
        parser.error("Provide --all or --cases")

    if args.emitter in CALIBRATION_ONLY and not args.calibration:
        parser.error(
            f"Emitter {args.emitter!r} is calibration-only (it replays ground truth). "
            "Re-run with --calibration to acknowledge this is NOT a real evaluation."
        )

    cases = load_cases()
    if args.cases:
        wanted = set(args.cases)
        missing = wanted - {c.case_id for c in cases}
        if missing:
            parser.error(f"Unknown case ids: {', '.join(sorted(missing))}")
        cases = [c for c in cases if c.case_id in wanted]

    results = []
    for case in cases:
        predictions = tuple(EMITTERS[args.emitter](case))
        ground_truth = load_ground_truth(case.directory, case.case_id)
        results.append(score_case(predictions, ground_truth, difficulty=case.difficulty))

    if args.emitter in CALIBRATION_ONLY:
        print(
            "WARNING: running calibration-only emitter "
            f"{args.emitter!r} (replays ground truth). Do NOT treat this as a "
            "real system evaluation.\n"
        )

    print(format_case_table(results))
    print(format_summary(results))

    export_dir = Path(args.export_dir)
    export_path = export_dir / f"{args.emitter}_{datetime.now():%Y%m%d_%H%M%S}.json"
    export_to_json(
        {"emitter": args.emitter, "case_ids": [c.case_id for c in cases]},
        results,
        export_path,
    )
    print(f"\nExported: {export_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())