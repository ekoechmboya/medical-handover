from datetime import datetime

from medical_handover.cases import (
    find_data_roots,
    load_cases,
    undated_records,
    validate_case,
)


def test_data_roots_discovered():
    assert len(find_data_roots()) == 2


def test_loads_all_15_cases():
    cases = load_cases()
    assert len(cases) == 15


def test_case_ids_are_exactly_01_to_15():
    ids = {c.case_id for c in load_cases()}
    assert ids == {f"case_{i:02d}" for i in range(1, 16)}


def test_all_profiles_carry_required_fields():
    for case in load_cases():
        assert case.patient_id.startswith("SYN-")
        assert case.age > 0
        assert case.sex in {"M", "F"}
        assert case.difficulty in {"easy", "medium", "hard"}
        assert case.title
        assert case.admission_reason
        assert case.current_location


def test_all_cases_validate_clean():
    for case in load_cases():
        assert validate_case(case) == [], f"{case.case_id}: {validate_case(case)}"


def test_every_case_has_handover_at_reference_time():
    for case in load_cases():
        assert case.handover.timestamp == datetime(2026, 8, 28, 18, 0), case.case_id


def test_timeline_is_sorted_and_never_after_handover():
    for case in load_cases():
        times = [r.effective_time for r in case.timeline if r.effective_time is not None]
        assert times == sorted(times), case.case_id
        for record in case.records:
            if record.effective_time is not None:
                assert record.effective_time <= case.handover.timestamp, (
                    f"{case.case_id}: {record.filename} after handover"
                )


def test_ground_truth_is_never_part_of_case_input():
    for case in load_cases():
        assert all(r.filename.endswith(".txt") for r in case.records)
        combined = "\n".join(r.text for r in case.records) + case.handover.text
        assert "ground_truth" not in combined, case.case_id


def test_undated_records_are_exposed_not_dropped():
    expected_undated = {
        "case_02": {"medication_history.txt"},
        "case_05": {"procedure_schedule.txt"},
        "case_13": {"medication_reconciliation.txt"},
        "case_14": {"imaging_request.txt", "lab_results.txt"},
    }
    for case in load_cases():
        undated = {r.filename for r in undated_records(case)}
        assert undated == expected_undated.get(case.case_id, set()), case.case_id


def test_partial_time_resolution():
    by_id = {c.case_id: c for c in load_cases()}
    for record in by_id["case_09"].records:
        if record.filename == "medication_history.txt":
            assert record.date_only.isoformat() == "2026-08-26"
    for record in by_id["case_15"].records:
        if record.filename == "historical_notes.txt":
            assert record.year_only == 2025


def test_record_header_times_parse():
    cases = {c.case_id: c for c in load_cases()}
    case_01 = cases["case_01"]
    stamps = {r.filename: r.timestamp for r in case_01.records}
    assert stamps["admission_note.txt"] == datetime(2026, 8, 28, 8, 10)
    assert stamps["nursing_notes.txt"] == datetime(2026, 8, 28, 13, 40)
    assert stamps["progress_note.txt"] == datetime(2026, 8, 28, 16, 15)