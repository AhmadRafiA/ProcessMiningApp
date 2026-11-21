"""Pytest fixtures and synthetic log generators for BPIC17 Analyzer tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from core.metrics import compute_activity_frequency, compute_case_summary
from core.models import LoadedDataset, LogOverview


def make_record(
    idx: int,
    case: str,
    act: str,
    ts: str,
    life: str = "complete",
    res: str = "U1",
) -> dict[str, Any]:
    """Helper to concisely create an event record dict without long lines."""
    return {
        "_orig_idx": idx,
        "case:concept:name": case,
        "concept:name": act,
        "time:timestamp": ts,
        "lifecycle:transition": life,
        "org:resource": res,
    }


def make_dataset_from_records(
    records: list[dict[str, Any]],
    dataset_name: str = "synthetic.xes",
    has_lifecycle: bool = True,
    has_resource: bool = True,
) -> LoadedDataset:
    """Create a fully-compliant LoadedDataset directly in memory for fast testing."""
    if not records:
        raw_df = pd.DataFrame(
            columns=[
                "_orig_idx",
                "case:concept:name",
                "concept:name",
                "time:timestamp",
                "lifecycle:transition",
                "org:resource",
            ]
        )
        raw_df["_orig_idx"] = raw_df["_orig_idx"].astype("int64")
        raw_df["case:concept:name"] = raw_df["case:concept:name"].astype("string")
        raw_df["concept:name"] = raw_df["concept:name"].astype("string")
        raw_df["time:timestamp"] = pd.to_datetime(
            raw_df["time:timestamp"], utc=True
        ).dt.as_unit("ns")
        raw_df["lifecycle:transition"] = raw_df["lifecycle:transition"].astype("string")
        raw_df["org:resource"] = raw_df["org:resource"].astype("string")
    else:
        raw_df = pd.DataFrame(records)
        if "_orig_idx" not in raw_df.columns:
            raw_df["_orig_idx"] = np.arange(len(raw_df), dtype=np.int64)
        else:
            raw_df["_orig_idx"] = raw_df["_orig_idx"].astype("int64")

        raw_df["case:concept:name"] = (
            raw_df["case:concept:name"].astype(str).str.strip().astype("string")
        )
        raw_df["concept:name"] = raw_df["concept:name"].astype(str).str.strip().astype("string")
        raw_df["time:timestamp"] = pd.to_datetime(
            raw_df["time:timestamp"], utc=True
        ).dt.as_unit("ns")

        if "lifecycle:transition" in raw_df.columns:
            l_str = raw_df["lifecycle:transition"].astype(str).str.strip()
            l_na = (
                raw_df["lifecycle:transition"].isna()
                | (l_str == "")
                | (l_str.str.lower() == "none")
            )
            raw_df["lifecycle:transition"] = l_str.mask(l_na, pd.NA).astype("string")
        else:
            raw_df["lifecycle:transition"] = pd.Series(pd.NA, index=raw_df.index, dtype="string")

        if "org:resource" in raw_df.columns:
            r_str = raw_df["org:resource"].astype(str).str.strip()
            r_na = (
                raw_df["org:resource"].isna()
                | (r_str == "")
                | r_str.str.lower().isin({"", "nan", "none", "null", "<na>"})
            )
            raw_df["org:resource"] = r_str.mask(r_na, pd.NA).astype("string")
        else:
            raw_df["org:resource"] = pd.Series(pd.NA, index=raw_df.index, dtype="string")

        # Stable sort mergesort
        raw_df = raw_df.sort_values(
            by=["case:concept:name", "time:timestamp", "_orig_idx"],
            ascending=[True, True, True],
            kind="mergesort",
        ).reset_index(drop=True)

    case_summary_df = compute_case_summary(raw_df)
    total_cases = int(len(case_summary_df))
    total_events = int(len(raw_df))
    activity_freq_df = compute_activity_frequency(raw_df, total_cases=total_cases)

    if total_cases > 0:
        mean_ct = float(case_summary_df["cycle_time_days"].mean())
        median_ct = float(case_summary_df["cycle_time_days"].median())
        start_utc = raw_df["time:timestamp"].min().to_pydatetime()
        end_utc = raw_df["time:timestamp"].max().to_pydatetime()
    else:
        mean_ct = 0.0
        median_ct = 0.0
        start_utc = pd.Timestamp.now(tz="UTC").to_pydatetime()
        end_utc = start_utc

    overview = LogOverview(
        dataset_filename=dataset_name,
        total_cases=total_cases,
        total_events=total_events,
        start_time_utc=start_utc,
        end_time_utc=end_utc,
        mean_cycle_time_days=mean_ct,
        median_cycle_time_days=median_ct,
        detected_attributes=(
            "case:concept:name",
            "concept:name",
            "time:timestamp",
            "lifecycle:transition",
            "org:resource",
        ),
        has_lifecycle=has_lifecycle,
        has_resource=has_resource,
        warnings=(),
    )

    return LoadedDataset(
        file_path=Path(dataset_name),
        overview=overview,
        raw_df=raw_df,
        case_summary_df=case_summary_df,
        activity_freq_df=activity_freq_df,
    )


@pytest.fixture
def empty_dataset() -> LoadedDataset:
    """Fixture providing an empty LoadedDataset."""
    return make_dataset_from_records([])


@pytest.fixture
def edge_cases_dataset() -> LoadedDataset:
    """Fixture containing traces for all canonical test scenarios T-01 through T-10."""
    records: list[dict[str, Any]] = [
        # T-01: Case_T01 O_Accepted on Day 1 and 5, trace duration Day 0 to Day 10 (10 days)
        make_record(1, "Case_T01", "A_Create", "2024-01-01T00:00:00Z"),
        make_record(2, "Case_T01", "O_Accepted", "2024-01-02T00:00:00Z"),
        make_record(3, "Case_T01", "O_Accepted", "2024-01-06T00:00:00Z", res="U2"),
        make_record(4, "Case_T01", "W_Complete", "2024-01-11T00:00:00Z"),

        # T-02: Case_T02 O_Cancelled in middle, followed by W_Call after offers
        make_record(5, "Case_T02", "A_Create", "2024-01-01T00:00:00Z"),
        make_record(6, "Case_T02", "O_Cancelled", "2024-01-02T00:00:00Z"),
        make_record(7, "Case_T02", "W_Call after offers", "2024-01-03T00:00:00Z"),

        # T-03: Case_T03 has both O_Accepted and O_Refused
        make_record(8, "Case_T03", "A_Create", "2024-01-01T00:00:00Z"),
        make_record(9, "Case_T03", "O_Accepted", "2024-01-02T00:00:00Z"),
        make_record(10, "Case_T03", "O_Refused", "2024-01-03T00:00:00Z"),

        # T-04: Case_T04 has identical timestamp at end: idx=11 (O_Accepted), idx=12 (O_Cancelled)
        make_record(11, "Case_T04", "O_Accepted", "2024-01-02T12:00:00Z"),
        make_record(12, "Case_T04", "O_Cancelled", "2024-01-02T12:00:00Z"),

        # T-05: Case_T05 has W_Assess Potential Fraud: 2x schedule, 1x start, 1x complete
        make_record(
            13, "Case_T05", "W_Assess Potential Fraud", "2024-01-01T00:00:00Z", life="schedule"
        ),
        make_record(
            14, "Case_T05", "W_Assess Potential Fraud", "2024-01-01T01:00:00Z", life="schedule"
        ),
        make_record(
            15, "Case_T05", "W_Assess Potential Fraud", "2024-01-01T02:00:00Z", life="start"
        ),
        make_record(
            16, "Case_T05", "W_Assess Potential Fraud", "2024-01-01T03:00:00Z", life="complete"
        ),

        # T-06: Case_T06 has W_Assess Potential Fraud with 'COMPLETE ' and ' complete'
        make_record(
            17, "Case_T06", "W_Assess Potential Fraud", "2024-01-01T00:00:00Z", life="COMPLETE "
        ),
        make_record(
            18, "Case_T06", "W_Assess Potential Fraud", "2024-01-01T01:00:00Z", life=" complete"
        ),

        # T-07: Case_T07 has 2 complete by User_1 and User_2
        make_record(
            19, "Case_T07", "W_Assess Potential Fraud", "2024-01-01T00:00:00Z", res="User_1"
        ),
        make_record(
            20, "Case_T07", "W_Assess Potential Fraud", "2024-01-01T01:00:00Z", res="User_2"
        ),

        # T-08: Case_T08 has 2 complete with empty resources
        make_record(21, "Case_T08", "W_Assess Potential Fraud", "2024-01-01T00:00:00Z", res=""),
        make_record(22, "Case_T08", "W_Assess Potential Fraud", "2024-01-01T01:00:00Z", res="   "),

        # T-09: Case_T09 has User_1 (2x complete) and User_2 (2x complete)
        make_record(
            23, "Case_T09", "W_Assess Potential Fraud", "2024-01-01T00:00:00Z", res="User_1"
        ),
        make_record(
            24, "Case_T09", "W_Assess Potential Fraud", "2024-01-01T01:00:00Z", res="User_1"
        ),
        make_record(
            25, "Case_T09", "W_Assess Potential Fraud", "2024-01-01T02:00:00Z", res="User_2"
        ),
        make_record(
            26, "Case_T09", "W_Assess Potential Fraud", "2024-01-01T03:00:00Z", res="User_2"
        ),

        # T-10a: Case_T10a: O_Cancelled -> A_Validating -> O_Accepted
        make_record(27, "Case_T10a", "O_Cancelled", "2024-01-01T00:00:00Z"),
        make_record(28, "Case_T10a", "A_Validating", "2024-01-01T01:00:00Z"),
        make_record(29, "Case_T10a", "O_Accepted", "2024-01-02T00:00:00Z"),

        # T-10b: Case_T10b: O_Accepted -> O_Cancelled (no later O_Accepted)
        make_record(30, "Case_T10b", "O_Accepted", "2024-01-01T00:00:00Z"),
        make_record(31, "Case_T10b", "O_Cancelled", "2024-01-01T01:00:00Z"),

        # T-10c: Case_T10c: O_Cancelled and O_Accepted same timestamp, _orig_idx 32 < 33
        make_record(32, "Case_T10c", "O_Cancelled", "2024-01-01T05:00:00Z"),
        make_record(33, "Case_T10c", "O_Accepted", "2024-01-01T05:00:00Z"),
    ]

    return make_dataset_from_records(records, dataset_name="edge_cases.xes")


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    """Ensure clean process exit on macOS when PySide6 and pm4py C extensions are unloaded."""
    import os

    if exitstatus == 0:
        os._exit(0)

