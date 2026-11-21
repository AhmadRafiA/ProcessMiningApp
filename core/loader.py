"""F01: XES / XES.GZ parsing via PM4Py, schema validation, and deterministic normalization."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pm4py

from core.models import (
    EmptyEventLogError,
    InvalidXESFormatError,
    MissingRequiredColumnsError,
    XESFileNotFoundError,
)

REQUIRED_COLUMNS: tuple[str, ...] = (
    "case:concept:name",
    "concept:name",
    "time:timestamp",
)
OPTIONAL_COLUMNS: tuple[str, ...] = (
    "lifecycle:transition",
    "org:resource",
)
CANONICAL_RESOURCE_NA_VALUES: frozenset[str] = frozenset({"", "nan", "none", "null", "<na>"})


def _validate_physical_file(path: Path) -> None:
    """Verify the XES/XES.GZ file exists, is non-empty, and has a supported extension."""
    if not path.exists() or not path.is_file():
        raise XESFileNotFoundError(path, detail="File tidak ditemukan.")
    if path.stat().st_size <= 0:
        raise XESFileNotFoundError(path, detail="Ukuran file 0 byte.")

    lower_name = path.name.lower()
    if not (lower_name.endswith(".xes") or lower_name.endswith(".xes.gz")):
        raise InvalidXESFormatError(
            f"Format file tidak didukung: '{path.name}'. Harap pilih file .xes atau .xes.gz."
        )


def _normalize_required_string_col(df: pd.DataFrame, col_name: str) -> pd.Series[Any]:
    """Ensure a required string column has no nulls/empty strings and is stripped."""
    series = df[col_name]
    if series.isna().any():
        raise InvalidXESFormatError(
            f"Kolom wajib '{col_name}' mengandung nilai kosong (NaN/None)."
        )
    normalized = series.astype(str).str.strip()
    if (normalized == "").any() or normalized.str.lower().isin({"nan", "none"}).any():
        raise InvalidXESFormatError(
            f"Kolom wajib '{col_name}' mengandung nilai string kosong atau tidak valid."
        )
    return normalized


def _normalize_resource_series(series: pd.Series[Any]) -> pd.Series[Any]:
    """Normalize empty, whitespace-only, or literal 'nan'/'none' resources to pd.NA."""
    is_na_mask = series.isna()
    as_str = series.astype(str).str.strip()
    empty_mask = is_na_mask | as_str.str.lower().isin(CANONICAL_RESOURCE_NA_VALUES)
    cleaned = as_str.mask(empty_mask, pd.NA)
    return cleaned.astype("string")


def load_xes_raw(
    file_path: str | Path,
) -> tuple[pd.DataFrame, bool, bool, tuple[str, ...]]:
    """Parse .xes/.xes.gz via PM4Py, validate columns, normalize UTC, and stable-sort.

    Returns:
        (raw_df, has_lifecycle, has_resource, detected_columns)
    """
    path = Path(file_path)
    _validate_physical_file(path)

    try:
        log = pm4py.read_xes(str(path))
        if isinstance(log, pd.DataFrame):
            df = log.copy()
        else:
            df = pm4py.convert_to_dataframe(log)
    except Exception as exc:
        raise InvalidXESFormatError(
            f"Gagal membaca file XES '{path.name}'. "
            "File mungkin rusak atau bukan format XES valid.",
            detail=str(exc),
        ) from exc

    if df.empty:
        raise EmptyEventLogError()

    detected_cols = tuple(str(col) for col in df.columns)

    # Embed _orig_idx immediately before any sorting or filtering
    df["_orig_idx"] = np.arange(len(df), dtype=np.int64)

    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_required:
        raise MissingRequiredColumnsError(missing_required)

    has_lifecycle = "lifecycle:transition" in df.columns
    has_resource = "org:resource" in df.columns

    df["case:concept:name"] = _normalize_required_string_col(df, "case:concept:name")
    df["concept:name"] = _normalize_required_string_col(df, "concept:name")

    try:
        df["time:timestamp"] = pd.to_datetime(
            df["time:timestamp"], utc=True, errors="raise"
        ).dt.as_unit("ns")
    except Exception as exc:
        raise InvalidXESFormatError(
            "Kolom 'time:timestamp' mengandung format waktu yang tidak dapat dikonversi ke UTC.",
            detail=str(exc),
        ) from exc

    if df["time:timestamp"].isna().any():
        raise InvalidXESFormatError("Kolom 'time:timestamp' mengandung nilai NaT (waktu kosong).")

    if has_lifecycle:
        lifecycle_na = df["lifecycle:transition"].isna()
        lifecycle_str = df["lifecycle:transition"].astype(str).str.strip()
        df["lifecycle:transition"] = lifecycle_str.mask(
            lifecycle_na | (lifecycle_str == ""), pd.NA
        ).astype("string")
    else:
        df["lifecycle:transition"] = pd.Series(pd.NA, index=df.index, dtype="string")

    if has_resource:
        df["org:resource"] = _normalize_resource_series(df["org:resource"])
    else:
        df["org:resource"] = pd.Series(pd.NA, index=df.index, dtype="string")

    # Deterministic stable sort: preserves _orig_idx order for identical timestamps
    df = df.sort_values(
        by=["case:concept:name", "time:timestamp", "_orig_idx"],
        ascending=[True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)

    return df, has_lifecycle, has_resource, detected_cols
