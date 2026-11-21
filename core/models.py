"""Single Source of Truth for domain data contracts and error taxonomy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

# Canonical Exercise Codes for Chapter 11
EXERCISE_CODES: tuple[str, ...] = (
    "11.7 A",
    "11.7 B",
    "11.7 C",
    "11.7 D",
    "11.7 E",
    "11.15",
    "11.18",
    "11.22",
)


class BPICAnalyzerError(Exception):
    """Base exception for all BPIC17 Analyzer domain errors."""

    def __init__(self, code: str, user_message: str, detail: str = "") -> None:
        self.code = code
        self.user_message = user_message
        self.detail = detail
        super().__init__(user_message if not detail else f"{user_message} ({detail})")


class XESFileNotFoundError(BPICAnalyzerError):
    """Raised when the target XES/XES.GZ file does not exist or is empty (0 bytes)."""

    def __init__(self, file_path: str | Path, detail: str = "") -> None:
        super().__init__(
            code="ERR_XES_NOT_FOUND",
            user_message=(
                f"File event log tidak ditemukan atau kosong (0 byte): {Path(file_path).name}"
            ),
            detail=detail,
        )


class InvalidXESFormatError(BPICAnalyzerError):
    """Raised when the file is corrupt, not valid XML/gzip, or fails pm4py.read_xes()."""

    def __init__(self, user_message: str, detail: str = "") -> None:
        super().__init__(
            code="ERR_XES_INVALID_FORMAT",
            user_message=user_message,
            detail=detail,
        )


class EmptyEventLogError(BPICAnalyzerError):
    """Raised when a valid XES file contains zero event rows."""

    def __init__(self, user_message: str = "File XES tidak memiliki baris event.") -> None:
        super().__init__(
            code="ERR_XES_EMPTY_LOG",
            user_message=user_message,
        )


class MissingRequiredColumnsError(BPICAnalyzerError):
    """Raised when any required XES attribute is missing from the loaded event log."""

    def __init__(self, missing_columns: tuple[str, ...] | list[str]) -> None:
        self.missing_columns = tuple(sorted(missing_columns))
        cols_str = ", ".join(self.missing_columns)
        super().__init__(
            code="ERR_XES_MISSING_REQ_COLS",
            user_message=f"Atribut wajib tidak ditemukan pada file XES: {cols_str}",
        )


class MissingOptionalAttributeError(BPICAnalyzerError):
    """Raised when an exercise requires an optional attribute absent in the dataset."""

    def __init__(self, attribute_name: str, exercise_code: str) -> None:
        self.attribute_name = attribute_name
        self.exercise_code = exercise_code
        super().__init__(
            code="ERR_ANALYZER_MISSING_OPT_COL",
            user_message=(
                f"Exercise {exercise_code} tidak dapat dijalankan karena atribut "
                f"'{attribute_name}' tidak tersedia di dataset ini."
            ),
        )


class ExportPrerequisiteError(BPICAnalyzerError):
    """Raised when CSV export is attempted before analysis results exist."""

    def __init__(
        self,
        user_message: str = "Jalankan analisis terlebih dahulu sebelum mengekspor hasil ke CSV.",
    ) -> None:
        super().__init__(
            code="ERR_EXPORT_PREREQUISITE",
            user_message=user_message,
        )


class CSVExportIOError(BPICAnalyzerError):
    """Raised when writing or atomically replacing a CSV output file fails."""

    def __init__(self, output_path: str | Path, detail: str = "") -> None:
        super().__init__(
            code="ERR_EXPORT_IO_PERMISSION",
            user_message=(
                f"Gagal menulis file CSV ke '{Path(output_path).name}'. "
                "Pastikan folder memiliki izin tulis dan file tidak sedang dibuka di aplikasi lain."
            ),
            detail=detail,
        )


@dataclass(frozen=True)
class LogOverview:
    """Basic summary statistics of the active event log for Overview page (F01 & F02)."""

    dataset_filename: str
    total_cases: int
    total_events: int
    start_time_utc: datetime
    end_time_utc: datetime
    mean_cycle_time_days: float
    median_cycle_time_days: float
    detected_attributes: tuple[str, ...]
    has_lifecycle: bool
    has_resource: bool
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class LoadedDataset:
    """In-memory read-only dataset bundle produced once per XES import."""

    file_path: Path
    overview: LogOverview
    raw_df: pd.DataFrame
    case_summary_df: pd.DataFrame
    activity_freq_df: pd.DataFrame


@dataclass
class AnalysisResult:
    """Uniform output contract for every Chapter 11 exercise analyzer."""

    exercise_code: str
    title: str
    filter_rule: str
    case_count: int
    total_cases: int
    mean_cycle_time_days: float | None
    percentage: float | None
    matched_cases_df: pd.DataFrame
    evidence_event_indices: dict[str, list[int]] = field(default_factory=dict)
