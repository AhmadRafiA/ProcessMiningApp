"""F02: Pre-computation of CaseSummaryTable, ActivityFrequencyTable, and LogOverview."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.loader import load_xes_raw
from core.models import LoadedDataset, LogOverview


def compute_case_summary(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Compute CaseSummaryTable from complete, deterministically sorted traces.

    Assumes raw_df is sorted by (case:concept:name, time:timestamp, _orig_idx).
    If called directly in tests with unsorted raw_df, sorts a local view first
    without mutating the caller's DataFrame.
    """
    if raw_df.empty:
        return pd.DataFrame(
            columns=[
                "case_id",
                "event_count",
                "start_time",
                "end_time",
                "cycle_time_days",
                "first_activity",
                "last_activity",
            ]
        )

    ordered = raw_df.sort_values(
        by=["case:concept:name", "time:timestamp", "_orig_idx"],
        ascending=[True, True, True],
        kind="mergesort",
    )

    grouped = ordered.groupby("case:concept:name", sort=True, observed=True)
    summary = grouped.agg(
        event_count=("concept:name", "size"),
        start_time=("time:timestamp", "first"),
        end_time=("time:timestamp", "last"),
        first_activity=("concept:name", "first"),
        last_activity=("concept:name", "last"),
    ).reset_index()

    summary = summary.rename(columns={"case:concept:name": "case_id"})
    summary["event_count"] = summary["event_count"].astype("int32")
    summary["cycle_time_days"] = (
        (summary["end_time"] - summary["start_time"]).dt.total_seconds() / 86400.0
    ).astype("float64")

    return summary[
        [
            "case_id",
            "event_count",
            "start_time",
            "end_time",
            "cycle_time_days",
            "first_activity",
            "last_activity",
        ]
    ]


def compute_activity_frequency(raw_df: pd.DataFrame, total_cases: int) -> pd.DataFrame:
    """Compute ActivityFrequencyTable ordered descending by event_count."""
    if raw_df.empty:
        return pd.DataFrame(
            columns=["activity_name", "event_count", "case_count", "case_coverage_pct"]
        )

    freq = (
        raw_df.groupby("concept:name", sort=False, observed=True)
        .agg(
            event_count=("concept:name", "size"),
            case_count=("case:concept:name", "nunique"),
        )
        .reset_index()
        .rename(columns={"concept:name": "activity_name"})
    )

    freq["event_count"] = freq["event_count"].astype("int64")
    freq["case_count"] = freq["case_count"].astype("int64")
    if total_cases > 0:
        freq["case_coverage_pct"] = (freq["case_count"] / float(total_cases) * 100.0).astype(
            "float64"
        )
    else:
        freq["case_coverage_pct"] = 0.0

    freq = freq.sort_values(
        by=["event_count", "activity_name"],
        ascending=[False, True],
        kind="mergesort",
    ).reset_index(drop=True)

    return freq[["activity_name", "event_count", "case_count", "case_coverage_pct"]]


def build_loaded_dataset(file_path: str | Path) -> LoadedDataset:
    """Facade: parse XES once, pre-compute case & activity summaries, and assemble LoadedDataset."""
    path = Path(file_path)
    raw_df, has_lifecycle, has_resource, detected_cols = load_xes_raw(path)
    case_summary_df = compute_case_summary(raw_df)

    total_cases = int(len(case_summary_df))
    total_events = int(len(raw_df))
    activity_freq_df = compute_activity_frequency(raw_df, total_cases=total_cases)

    warnings_list: list[str] = []
    if not has_lifecycle:
        warnings_list.append(
            "Kolom 'lifecycle:transition' tidak ditemukan; "
            "Exercise 11.15 dan 11.18 tidak dapat dijalankan."
        )
    if not has_resource:
        warnings_list.append(
            "Kolom 'org:resource' tidak ditemukan; Exercise 11.18 tidak dapat dijalankan."
        )

    overview = LogOverview(
        dataset_filename=path.name,
        total_cases=total_cases,
        total_events=total_events,
        start_time_utc=raw_df["time:timestamp"].min().to_pydatetime(),
        end_time_utc=raw_df["time:timestamp"].max().to_pydatetime(),
        mean_cycle_time_days=float(case_summary_df["cycle_time_days"].mean()),
        median_cycle_time_days=float(case_summary_df["cycle_time_days"].median()),
        detected_attributes=detected_cols,
        has_lifecycle=has_lifecycle,
        has_resource=has_resource,
        warnings=tuple(warnings_list),
    )

    return LoadedDataset(
        file_path=path,
        overview=overview,
        raw_df=raw_df,
        case_summary_df=case_summary_df,
        activity_freq_df=activity_freq_df,
    )
