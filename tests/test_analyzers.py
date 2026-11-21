"""Comprehensive unit test suite for core.analyzers covering T-01 through T-10."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from core.analyzers import (
    analyze_exercise_11_7,
    analyze_exercise_11_15,
    analyze_exercise_11_18,
    analyze_exercise_11_22,
    extract_case_trace,
    run_all_required_analyses,
)
from core.models import (
    LoadedDataset,
    MissingOptionalAttributeError,
)
from tests.conftest import make_dataset_from_records, make_record


def test_core_analyzers_has_zero_pyside6_imports() -> None:
    """Invariant: core/analyzers.py must never import PySide6."""
    path = Path(__file__).resolve().parent.parent / "core" / "analyzers.py"
    text = path.read_text(encoding="utf-8")
    assert "PySide6" not in text, "Forbidden PySide6 import found in core/analyzers.py"


def test_t01_exercise_11_7_c_multi_occurrence_whole_trace_cycle_time() -> None:
    """T-01: 1 case with O_Accepted twice on Day 1 and Day 5; trace duration is 10 days."""
    records: list[dict[str, Any]] = [
        make_record(1, "C1", "Start", "2024-01-01T00:00:00Z"),
        make_record(2, "C1", "O_Accepted", "2024-01-02T00:00:00Z"),
        make_record(3, "C1", "O_Accepted", "2024-01-06T00:00:00Z"),
        make_record(4, "C1", "End", "2024-01-11T00:00:00Z"),
    ]
    ds = make_dataset_from_records(records)
    results = analyze_exercise_11_7(ds)
    res_c = results["11.7 C"]

    assert res_c.case_count == 1
    assert res_c.mean_cycle_time_days == pytest.approx(10.0)
    assert res_c.evidence_event_indices["C1"] == [2, 3]

    matched_row = res_c.matched_cases_df.iloc[0]
    assert matched_row["case_id"] == "C1"
    assert matched_row["cycle_time_days"] == pytest.approx(10.0)
    assert matched_row["matching_event_count"] == 2
    assert matched_row["event_count"] == 4


def test_t02_exercise_11_7_e_cancelled_in_middle_rejected() -> None:
    """T-02: 1 case with O_Cancelled in the middle followed by another activity fails 11.7 E."""
    records: list[dict[str, Any]] = [
        make_record(1, "C1", "Start", "2024-01-01T00:00:00Z"),
        make_record(2, "C1", "O_Cancelled", "2024-01-02T00:00:00Z"),
        make_record(3, "C1", "W_Call after offers", "2024-01-03T00:00:00Z"),
    ]
    ds = make_dataset_from_records(records)
    results = analyze_exercise_11_7(ds)
    res_e = results["11.7 E"]

    assert res_e.case_count == 0
    assert res_e.matched_cases_df.empty
    assert res_e.evidence_event_indices == {}


def test_t03_exercise_11_7_c_and_d_non_exclusive() -> None:
    """T-03: 1 case with both O_Accepted and O_Refused qualifies for both independently."""
    records: list[dict[str, Any]] = [
        make_record(1, "C1", "Start", "2024-01-01T00:00:00Z"),
        make_record(2, "C1", "O_Accepted", "2024-01-02T00:00:00Z"),
        make_record(3, "C1", "O_Refused", "2024-01-03T00:00:00Z"),
    ]
    ds = make_dataset_from_records(records)
    results = analyze_exercise_11_7(ds)

    assert results["11.7 C"].case_count == 1
    assert results["11.7 D"].case_count == 1
    assert "C1" in results["11.7 C"].evidence_event_indices
    assert "C1" in results["11.7 D"].evidence_event_indices


def test_t04_exercise_11_7_e_identical_timestamps_resolved_by_orig_idx() -> None:
    """T-04: Identical timestamps on last 2 events; _orig_idx determines last activity."""
    # Order A: idx=1 is O_Accepted, idx=2 is O_Cancelled -> last is O_Cancelled -> qualifies
    records_pass: list[dict[str, Any]] = [
        make_record(1, "C1", "O_Accepted", "2024-01-02T00:00:00Z"),
        make_record(2, "C1", "O_Cancelled", "2024-01-02T00:00:00Z"),
    ]
    ds_pass = make_dataset_from_records(records_pass)
    res_pass = analyze_exercise_11_7(ds_pass)["11.7 E"]
    assert res_pass.case_count == 1
    assert res_pass.evidence_event_indices["C1"] == [2]

    # Order B: idx=1 is O_Cancelled, idx=2 is O_Accepted -> last is O_Accepted -> fails
    records_fail: list[dict[str, Any]] = [
        make_record(1, "C1", "O_Cancelled", "2024-01-02T00:00:00Z"),
        make_record(2, "C1", "O_Accepted", "2024-01-02T00:00:00Z"),
    ]
    ds_fail = make_dataset_from_records(records_fail)
    res_fail = analyze_exercise_11_7(ds_fail)["11.7 E"]
    assert res_fail.case_count == 0


def test_t05_exercise_11_15_lifecycle_strict_filtering() -> None:
    """T-05: 2x schedule, 1x start, 1x complete for W_Assess Potential Fraud fails 11.15."""
    records: list[dict[str, Any]] = [
        make_record(1, "C1", "W_Assess Potential Fraud", "2024-01-01T00:00:00Z", life="schedule"),
        make_record(2, "C1", "W_Assess Potential Fraud", "2024-01-01T01:00:00Z", life="schedule"),
        make_record(3, "C1", "W_Assess Potential Fraud", "2024-01-01T02:00:00Z", life="start"),
        make_record(4, "C1", "W_Assess Potential Fraud", "2024-01-01T03:00:00Z", life="complete"),
    ]
    ds = make_dataset_from_records(records)
    res = analyze_exercise_11_15(ds)
    assert res.case_count == 0
    assert res.matched_cases_df.empty


def test_t06_exercise_11_15_case_and_whitespace_normalization() -> None:
    """T-06: W_Assess Potential Fraud with 'COMPLETE ' and ' complete' qualifies 11.15."""
    records: list[dict[str, Any]] = [
        make_record(1, "C1", "W_Assess Potential Fraud", "2024-01-01T00:00:00Z", life="COMPLETE "),
        make_record(2, "C1", "W_Assess Potential Fraud", "2024-01-01T01:00:00Z", life=" complete"),
    ]
    ds = make_dataset_from_records(records)
    res = analyze_exercise_11_15(ds)
    assert res.case_count == 1
    assert res.evidence_event_indices["C1"] == [1, 2]
    assert res.matched_cases_df.iloc[0]["complete_count"] == 2


def test_t07_exercise_11_15_vs_11_18_different_resources() -> None:
    """T-07: 2 complete by User_1 and User_2 qualifies 11.15, but fails 11.18."""
    records: list[dict[str, Any]] = [
        make_record(1, "C1", "W_Assess Potential Fraud", "2024-01-01T00:00:00Z", res="User_1"),
        make_record(2, "C1", "W_Assess Potential Fraud", "2024-01-01T01:00:00Z", res="User_2"),
    ]
    ds = make_dataset_from_records(records)
    res_15 = analyze_exercise_11_15(ds)
    res_18 = analyze_exercise_11_18(ds)

    assert res_15.case_count == 1
    assert res_18.case_count == 0


def test_t08_exercise_11_18_empty_resources_rejected() -> None:
    """T-08: 2 complete with empty/whitespace resource fails 11.18."""
    records: list[dict[str, Any]] = [
        make_record(1, "C1", "W_Assess Potential Fraud", "2024-01-01T00:00:00Z", res=""),
        make_record(2, "C1", "W_Assess Potential Fraud", "2024-01-01T01:00:00Z", res="   "),
        make_record(3, "C1", "W_Assess Potential Fraud", "2024-01-01T02:00:00Z", res="nan"),
    ]
    ds = make_dataset_from_records(records)
    res_18 = analyze_exercise_11_18(ds)
    assert res_18.case_count == 0


def test_t09_exercise_11_18_multi_resource_qualifying_counted_once() -> None:
    """T-09: User_1 (2x complete) and User_2 (2x complete) counted as 1 case in 11.18."""
    records: list[dict[str, Any]] = [
        make_record(1, "C1", "W_Assess Potential Fraud", "2024-01-01T00:00:00Z", res="User_1"),
        make_record(2, "C1", "W_Assess Potential Fraud", "2024-01-01T01:00:00Z", res="User_1"),
        make_record(3, "C1", "W_Assess Potential Fraud", "2024-01-01T02:00:00Z", res="User_2"),
        make_record(4, "C1", "W_Assess Potential Fraud", "2024-01-01T03:00:00Z", res="User_2"),
    ]
    ds = make_dataset_from_records(records)
    res_18 = analyze_exercise_11_18(ds)

    assert res_18.case_count == 1
    row = res_18.matched_cases_df.iloc[0]
    assert row["case_id"] == "C1"
    assert row["matching_resources"] == "User_1, User_2"
    assert row["max_resource_complete_count"] == 2
    assert row["total_fraud_complete_count"] == 4
    assert sorted(res_18.evidence_event_indices["C1"]) == [1, 2, 3, 4]


def test_t10_exercise_11_22_eventually_follows_scenarios() -> None:
    """T-10: (a) sequence pattern qualifies; (b) reverse order fails; (c) same timestamp."""
    # 10a: separated by another activity
    records_a: list[dict[str, Any]] = [
        make_record(1, "Ca", "O_Cancelled", "2024-01-01T00:00:00Z"),
        make_record(2, "Ca", "A_Validating", "2024-01-01T01:00:00Z"),
        make_record(3, "Ca", "O_Accepted", "2024-01-01T02:00:00Z"),
    ]
    ds_a = make_dataset_from_records(records_a)
    res_a = analyze_exercise_11_22(ds_a)
    assert res_a.case_count == 1
    assert res_a.evidence_event_indices["Ca"] == [1, 3]

    # 10b: O_Accepted before O_Cancelled without later O_Accepted
    records_b: list[dict[str, Any]] = [
        make_record(1, "Cb", "O_Accepted", "2024-01-01T00:00:00Z"),
        make_record(2, "Cb", "O_Cancelled", "2024-01-01T01:00:00Z"),
    ]
    ds_b = make_dataset_from_records(records_b)
    res_b = analyze_exercise_11_22(ds_b)
    assert res_b.case_count == 0

    # 10c: same timestamp, _orig_idx 5 (O_Cancelled) < 6 (O_Accepted)
    records_c: list[dict[str, Any]] = [
        make_record(5, "Cc", "O_Cancelled", "2024-01-01T05:00:00Z"),
        make_record(6, "Cc", "O_Accepted", "2024-01-01T05:00:00Z"),
    ]
    ds_c = make_dataset_from_records(records_c)
    res_c = analyze_exercise_11_22(ds_c)
    assert res_c.case_count == 1
    assert res_c.evidence_event_indices["Cc"] == [5, 6]


def test_missing_optional_attributes_error_and_orchestrator() -> None:
    """Verify MissingOptionalAttributeError when lifecycle/resource are absent."""
    records: list[dict[str, Any]] = [
        make_record(1, "C1", "Start", "2024-01-01T00:00:00Z"),
        make_record(2, "C1", "End", "2024-01-02T00:00:00Z"),
    ]
    ds_no_opt = make_dataset_from_records(records, has_lifecycle=False, has_resource=False)

    with pytest.raises(MissingOptionalAttributeError) as exc_15:
        analyze_exercise_11_15(ds_no_opt)
    assert exc_15.value.attribute_name == "lifecycle:transition"

    with pytest.raises(MissingOptionalAttributeError) as exc_18:
        analyze_exercise_11_18(ds_no_opt)
    assert exc_18.value.attribute_name == "lifecycle:transition"

    # Orchestrator handles gracefully
    all_res = run_all_required_analyses(ds_no_opt)
    assert len(all_res) == 8
    assert all_res["11.15"].case_count == 0
    assert "[TIDAK TERSEDIA]" in all_res["11.15"].filter_rule
    assert all_res["11.18"].case_count == 0
    assert "[TIDAK TERSEDIA]" in all_res["11.18"].filter_rule


def test_extract_case_trace(edge_cases_dataset: LoadedDataset) -> None:
    """Test extract_case_trace with valid case and highlights, and non-existent case."""
    trace_df = extract_case_trace(edge_cases_dataset, "Case_T01", highlight_indices={2, 3})
    assert len(trace_df) == 4
    assert list(trace_df.columns) == [
        "step_no",
        "_orig_idx",
        "time:timestamp",
        "concept:name",
        "lifecycle:transition",
        "org:resource",
        "is_evidence",
        "evidence_badge",
    ]
    assert trace_df.iloc[0]["step_no"] == 1
    assert bool(trace_df.iloc[1]["is_evidence"]) is True
    assert trace_df.iloc[1]["evidence_badge"] == "[EVIDENCE]"
    assert bool(trace_df.iloc[0]["is_evidence"]) is False
    assert trace_df.iloc[0]["evidence_badge"] == ""

    # Non-existent case
    empty_trace = extract_case_trace(edge_cases_dataset, "Non_Existent_Case")
    assert empty_trace.empty
    assert "step_no" in empty_trace.columns


def test_empty_dataset_analyzers(empty_dataset: LoadedDataset) -> None:
    """Boundary test: running analyzers on an empty dataset produces 0 cases without errors."""
    all_res = run_all_required_analyses(empty_dataset)
    assert len(all_res) == 8
    for _code, res in all_res.items():
        assert res.case_count == 0
        assert res.total_cases == 0
        assert res.percentage == 0.0
        assert res.matched_cases_df.empty
