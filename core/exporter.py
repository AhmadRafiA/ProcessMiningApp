"""Atomic CSV export engine (F07) for summary results and exercise matched cases.

Pure Python domain layer — Zero Qt / GUI imports!
"""

from __future__ import annotations

import csv
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.models import (
    EXERCISE_CODES,
    AnalysisResult,
    CSVExportIOError,
    ExportPrerequisiteError,
)

# Canonical column ordering per exercise for cases_<exercise_code>.csv
CASES_COLUMNS_BY_EXERCISE: dict[str, list[str]] = {
    "11.7 C": [
        "case_id",
        "cycle_time_days",
        "event_count",
        "last_activity",
        "matching_event_count",
        "evidence_orig_indices",
    ],
    "11.7 D": [
        "case_id",
        "cycle_time_days",
        "event_count",
        "last_activity",
        "matching_event_count",
        "evidence_orig_indices",
    ],
    "11.7 E": [
        "case_id",
        "cycle_time_days",
        "event_count",
        "last_activity",
        "matching_event_count",
        "evidence_orig_indices",
    ],
    "11.15": [
        "case_id",
        "complete_count",
        "cycle_time_days",
        "event_count",
        "evidence_orig_indices",
    ],
    "11.18": [
        "case_id",
        "matching_resources",
        "max_resource_complete_count",
        "total_fraud_complete_count",
        "cycle_time_days",
        "event_count",
        "evidence_orig_indices",
    ],
    "11.22": [
        "case_id",
        "first_cancelled_idx",
        "first_cancelled_time",
        "following_accepted_idx",
        "following_accepted_time",
        "cycle_time_days",
        "event_count",
        "evidence_orig_indices",
    ],
}


def get_canonical_exercise_csv_filename(exercise_code: str) -> str:
    """Generate canonical filename for an exercise cases CSV export."""
    slug = exercise_code.strip().replace(".", "_").replace(" ", "_")
    return f"cases_{slug}.csv"


def export_summary_csv(
    results: dict[str, AnalysisResult],
    dataset_filename: str,
    output_path: str | Path,
) -> Path:
    """Export 8-row canonical summary results to CSV atomically.

    Parameters
    ----------
    results : dict[str, AnalysisResult]
        Dictionary of computed results for EXERCISE_CODES.
    dataset_filename : str
        Source filename of the dataset (sanitized to basename).
    output_path : str | Path
        Target CSV file path.

    Returns
    -------
    Path
        Resolved path of the created CSV file.

    Raises
    ------
    ExportPrerequisiteError
        If results dictionary is empty or missing required exercise results.
    CSVExportIOError
        If writing or replacing the output file fails due to I/O or permissions.
    """
    if not results:
        raise ExportPrerequisiteError(
            "Dictionary hasil analisis kosong. Jalankan analisis terlebih dahulu."
        )

    # Validate that all required canonical exercise codes are present
    missing = [c for c in EXERCISE_CODES if c not in results]
    if missing:
        raise ExportPrerequisiteError(
            f"Hasil analisis belum lengkap. Soal yang belum ada: {', '.join(missing)}."
        )

    target_path = Path(output_path).resolve()
    temp_path = target_path.with_name(f"{target_path.name}.tmp")

    # Sanitize dataset_filename to avoid leaking OS directory paths
    clean_dataset_name = Path(dataset_filename).name
    current_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    rows: list[dict[str, Any]] = []
    for code in EXERCISE_CODES:
        res = results[code]
        pct_val: Any = round(res.percentage, 4) if res.percentage is not None else ""
        dur_val: Any = (
            round(res.mean_cycle_time_days, 4) if res.mean_cycle_time_days is not None else ""
        )

        rows.append(
            {
                "exercise_code": res.exercise_code,
                "title": res.title,
                "filter_rule": res.filter_rule,
                "case_count": res.case_count,
                "total_cases_denominator": res.total_cases,
                "percentage": pct_val,
                "mean_cycle_time_days": dur_val,
                "dataset_filename": clean_dataset_name,
                "executed_at": current_utc,
            }
        )

    summary_df = pd.DataFrame(rows)

    try:
        # Atomic write: write to temp file first, then replace
        summary_df.to_csv(
            temp_path,
            index=False,
            encoding="utf-8-sig",
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )
        os.replace(temp_path, target_path)
    except (PermissionError, OSError) as exc:
        if temp_path.exists():
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise CSVExportIOError(target_path, detail=str(exc)) from exc

    return target_path


def export_exercise_cases_csv(
    result: AnalysisResult,
    output_path: str | Path,
) -> Path:
    """Export matched cases for a specific exercise to CSV atomically with evidence trace indices.

    Parameters
    ----------
    result : AnalysisResult
        Analysis result containing matched_cases_df and evidence_event_indices.
    output_path : str | Path
        Target CSV file path.

    Returns
    -------
    Path
        Resolved path of the created CSV file.

    Raises
    ------
    ExportPrerequisiteError
        If result or matched_cases_df is not available.
    CSVExportIOError
        If writing or replacing the output file fails due to I/O or permissions.
    """
    if result.matched_cases_df is None:
        raise ExportPrerequisiteError(
            f"Tabel kasus untuk soal '{result.exercise_code}' tidak tersedia."
        )

    target_path = Path(output_path).resolve()
    temp_path = target_path.with_name(f"{target_path.name}.tmp")

    df = result.matched_cases_df.copy()
    code = result.exercise_code

    # Build evidence_orig_indices column (semicolon-separated list of orig_idx)
    if "case_id" in df.columns:
        evidence_col: list[str] = []
        for cid in df["case_id"]:
            indices = result.evidence_event_indices.get(str(cid).strip(), [])
            evidence_col.append(";".join(str(idx) for idx in indices))
        df["evidence_orig_indices"] = evidence_col
    else:
        df["evidence_orig_indices"] = ""

    # Round floating-point columns (e.g. cycle_time_days) to 4 decimals
    for col in df.select_dtypes(include=["float", "float32", "float64"]).columns:
        df[col] = df[col].round(4)

    # Reorder or select canonical columns if defined for this exercise
    expected_cols = CASES_COLUMNS_BY_EXERCISE.get(code)
    if expected_cols is not None:
        # Include all expected columns, creating empty ones if missing
        for col_name in expected_cols:
            if col_name not in df.columns:
                df[col_name] = ""
        df = df[expected_cols]

    try:
        # Atomic write: write to temp file first, then replace
        df.to_csv(
            temp_path,
            index=False,
            encoding="utf-8-sig",
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )
        os.replace(temp_path, target_path)
    except (PermissionError, OSError) as exc:
        if temp_path.exists():
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise CSVExportIOError(target_path, detail=str(exc)) from exc

    return target_path


def export_filtered_cases_csv(
    filtered_cases_df: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    """Export filtered case summary table to CSV atomically with utf-8-sig encoding."""
    target_path = Path(output_path).resolve()
    temp_path = target_path.with_name(f"{target_path.name}.tmp")

    df = filtered_cases_df.copy()
    for col in df.select_dtypes(include=["float", "float32", "float64"]).columns:
        df[col] = df[col].round(4)

    try:
        df.to_csv(
            temp_path,
            index=False,
            encoding="utf-8-sig",
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )
        os.replace(temp_path, target_path)
    except (PermissionError, OSError) as exc:
        if temp_path.exists():
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise CSVExportIOError(target_path, detail=str(exc)) from exc

    return target_path

