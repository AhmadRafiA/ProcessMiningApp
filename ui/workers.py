"""QThread workers for background XES import and analytics execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from core.analyzers import (
    analyze_exercise_11_7,
    analyze_exercise_11_15,
    analyze_exercise_11_18,
    analyze_exercise_11_22,
)
from core.metrics import build_loaded_dataset
from core.models import (
    AnalysisResult,
    BPICAnalyzerError,
    LoadedDataset,
    MissingOptionalAttributeError,
)


class ImportWorker(QObject):
    """Background worker for loading and pre-computing event logs in a separate QThread."""

    progress_updated = Signal(int, str)
    import_succeeded = Signal(object)
    import_failed = Signal(str, str)

    def __init__(self, file_path: str | Path, parent: Any = None) -> None:
        super().__init__(parent)
        self.file_path = Path(file_path)
        self._is_cancelled: bool = False

    def cancel(self) -> None:
        """Request worker cancellation."""
        self._is_cancelled = True

    def run(self) -> None:
        """Execute parsing and metrics pre-calculation."""
        try:
            if self._is_cancelled:
                return

            self.progress_updated.emit(10, f"Membuka file {self.file_path.name}...")
            if self._is_cancelled:
                return

            self.progress_updated.emit(35, "Memvalidasi atribut dan menormalisasi urutan...")
            dataset = build_loaded_dataset(self.file_path)

            if self._is_cancelled:
                return

            self.progress_updated.emit(90, "Menyusun ringkasan statistik...")
            if self._is_cancelled:
                return

            self.progress_updated.emit(100, "Dataset siap.")
            self.import_succeeded.emit(dataset)

        except BPICAnalyzerError as err:
            self.import_failed.emit(err.code, err.user_message)
        except Exception as exc:  # noqa: BLE001
            self.import_failed.emit("ERR_IMPORT_UNKNOWN", f"Terjadi kesalahan tak terduga: {exc}")


class AnalysisWorker(QObject):
    """Background worker for executing Chapter 11 analytics in a separate QThread."""

    progress_updated = Signal(int, str)
    analysis_succeeded = Signal(object)
    analysis_failed = Signal(str, str)

    def __init__(self, dataset: LoadedDataset, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset = dataset
        self._is_cancelled: bool = False

    def cancel(self) -> None:
        """Request worker cancellation."""
        self._is_cancelled = True

    def run(self) -> None:
        """Run all 8 Chapter 11 analytical exercises sequentially."""
        try:
            if self._is_cancelled:
                return

            results: dict[str, AnalysisResult] = {}

            # Step 1: Exercise 11.7 (A-E)
            self.progress_updated.emit(15, "Menghitung Exercise 11.7 (A–E)...")
            res_11_7 = analyze_exercise_11_7(self.dataset)
            results.update(res_11_7)
            if self._is_cancelled:
                return

            # Step 2: Exercise 11.15
            self.progress_updated.emit(40, "Menghitung Exercise 11.15 (Pengulangan Fraud)...")
            try:
                results["11.15"] = analyze_exercise_11_15(self.dataset)
            except MissingOptionalAttributeError as err:
                from core.analyzers import _build_empty_matched_11_15

                results["11.15"] = AnalysisResult(
                    exercise_code="11.15",
                    title="Repeated Activity (Fraud Complete >= 2) [UNAVAILABLE]",
                    filter_rule=f"[TIDAK TERSEDIA] {err.user_message}",
                    case_count=0,
                    total_cases=self.dataset.overview.total_cases,
                    mean_cycle_time_days=None,
                    percentage=0.0,
                    matched_cases_df=_build_empty_matched_11_15(),
                    evidence_event_indices={},
                )
            if self._is_cancelled:
                return

            # Step 3: Exercise 11.18
            self.progress_updated.emit(65, "Menghitung Exercise 11.18 (Pengulangan Resource)...")
            try:
                results["11.18"] = analyze_exercise_11_18(self.dataset)
            except MissingOptionalAttributeError as err:
                from core.analyzers import _build_empty_matched_11_18

                results["11.18"] = AnalysisResult(
                    exercise_code="11.18",
                    title="Repeated Activity by Same Resource [UNAVAILABLE]",
                    filter_rule=f"[TIDAK TERSEDIA] {err.user_message}",
                    case_count=0,
                    total_cases=self.dataset.overview.total_cases,
                    mean_cycle_time_days=None,
                    percentage=0.0,
                    matched_cases_df=_build_empty_matched_11_18(),
                    evidence_event_indices={},
                )
            if self._is_cancelled:
                return

            # Step 4: Exercise 11.22
            self.progress_updated.emit(85, "Menghitung Exercise 11.22 (Urutan Event)...")
            results["11.22"] = analyze_exercise_11_22(self.dataset)
            if self._is_cancelled:
                return

            self.progress_updated.emit(100, "Seluruh analisis berhasil dihitung.")
            self.analysis_succeeded.emit(results)

        except BPICAnalyzerError as err:
            self.analysis_failed.emit(err.code, err.user_message)
        except Exception as exc:  # noqa: BLE001
            self.analysis_failed.emit(
                "ERR_ANALYSIS_UNKNOWN", f"Terjadi kesalahan saat analisis: {exc}"
            )
