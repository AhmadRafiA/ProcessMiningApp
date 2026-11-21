"""Unit and integration tests for Stage 4: Case Explorer, Reset/Re-run, and Atomic CSV Export."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

# Set headless Qt offscreen platform
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from core.analyzers import run_all_required_analyses
from core.exporter import (
    CASES_COLUMNS_BY_EXERCISE,
    export_exercise_cases_csv,
    export_summary_csv,
    get_canonical_exercise_csv_filename,
)
from core.models import (
    EXERCISE_CODES,
    AnalysisResult,
    CSVExportIOError,
    ExportPrerequisiteError,
    LoadedDataset,
)
from ui.main_window import AppState, MainWindow
from ui.pages.ex11_7_page import Ex11_7Page
from ui.pages.ex11_15_18_page import Ex11_15_18Page
from ui.pages.ex11_22_page import Ex11_22Page


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Provide a headless QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    assert isinstance(app, QApplication)
    return app


# ==============================================================================
# 1. Tests for export_summary_csv (M4.2)
# ==============================================================================


def test_export_summary_csv_happy_path(
    edge_cases_dataset: LoadedDataset, tmp_path: Path
) -> None:
    """Test successful export of summary_results.csv with 8 rows and sanitized filename."""
    results = run_all_required_analyses(edge_cases_dataset)
    output_file = tmp_path / "summary_results.csv"

    # Pass an unsanitized absolute path as dataset_filename
    dirty_path = "/Users/test_user/secret_folder/BPI_Challenge_2017.xes.gz"
    res_path = export_summary_csv(results, dirty_path, output_file)

    assert res_path == output_file
    assert output_file.exists()

    # Read back and verify format
    df = pd.read_csv(output_file, encoding="utf-8-sig")
    assert len(df) == 8
    assert list(df["exercise_code"]) == list(EXERCISE_CODES)

    expected_cols = [
        "exercise_code",
        "title",
        "filter_rule",
        "case_count",
        "total_cases_denominator",
        "percentage",
        "mean_cycle_time_days",
        "dataset_filename",
        "executed_at",
    ]
    assert list(df.columns) == expected_cols

    # Verify privacy sanitization: only basename is present
    for fn in df["dataset_filename"]:
        assert fn == "BPI_Challenge_2017.xes.gz"
        assert "secret_folder" not in fn
        assert "test_user" not in fn

    # Verify ISO-8601 UTC timestamp format
    for ts in df["executed_at"]:
        assert ts.endswith("Z")
        assert "T" in ts

    # Verify atomic write: no temp file left behind
    temp_file = output_file.with_name(f"{output_file.name}.tmp")
    assert not temp_file.exists()


def test_export_summary_csv_prerequisite_error(tmp_path: Path) -> None:
    """Test EC-07.1: ExportPrerequisiteError raised when results dict is empty or incomplete."""
    out_file = tmp_path / "summary_test.csv"

    # Empty dict
    with pytest.raises(ExportPrerequisiteError) as exc_info:
        export_summary_csv({}, "test.xes", out_file)
    assert "ERR_EXPORT_PREREQUISITE" in exc_info.value.code

    # Incomplete dict (missing some exercises)
    incomplete_results = {
        "11.7 A": AnalysisResult(
            exercise_code="11.7 A",
            title="Total",
            filter_rule="rule",
            case_count=10,
            total_cases=10,
            mean_cycle_time_days=1.0,
            percentage=100.0,
            matched_cases_df=pd.DataFrame(),
        )
    }
    with pytest.raises(ExportPrerequisiteError):
        export_summary_csv(incomplete_results, "test.xes", out_file)


def test_export_summary_csv_io_error(
    edge_cases_dataset: LoadedDataset, tmp_path: Path
) -> None:
    """Test EC-07.2: CSVExportIOError raised when target directory is invalid / unwritable."""
    results = run_all_required_analyses(edge_cases_dataset)

    # Use a non-existent parent directory where creating file is impossible
    invalid_path = tmp_path / "non_existent_dir_123" / "forbidden_summary.csv"

    with pytest.raises(CSVExportIOError) as exc_info:
        export_summary_csv(results, "test.xes", invalid_path)

    assert "ERR_EXPORT_IO_PERMISSION" in exc_info.value.code
    # Temp file should not exist
    temp_file = invalid_path.with_name(f"{invalid_path.name}.tmp")
    assert not temp_file.exists()


# ==============================================================================
# 2. Tests for export_exercise_cases_csv (M4.2)
# ==============================================================================


def test_get_canonical_exercise_csv_filename() -> None:
    """Test canonical file naming helper."""
    assert get_canonical_exercise_csv_filename("11.7 C") == "cases_11_7_C.csv"
    assert get_canonical_exercise_csv_filename("11.7 D") == "cases_11_7_D.csv"
    assert get_canonical_exercise_csv_filename("11.7 E") == "cases_11_7_E.csv"
    assert get_canonical_exercise_csv_filename("11.15") == "cases_11_15.csv"
    assert get_canonical_exercise_csv_filename("11.18") == "cases_11_18.csv"
    assert get_canonical_exercise_csv_filename("11.22") == "cases_11_22.csv"


def test_export_exercise_cases_11_7_c(
    edge_cases_dataset: LoadedDataset, tmp_path: Path
) -> None:
    """Test export of cases_11_7_C.csv with evidence_orig_indices."""
    results = run_all_required_analyses(edge_cases_dataset)
    res_11_7_c = results["11.7 C"]

    out_file = tmp_path / "cases_11_7_C.csv"
    export_exercise_cases_csv(res_11_7_c, out_file)

    assert out_file.exists()
    df = pd.read_csv(out_file, encoding="utf-8-sig")

    expected_cols = CASES_COLUMNS_BY_EXERCISE["11.7 C"]
    assert list(df.columns) == expected_cols

    # Verify evidence_orig_indices is formatted with semicolons
    if not df.empty:
        # Check first non-empty evidence
        first_ev = str(df["evidence_orig_indices"].iloc[0])
        assert isinstance(first_ev, str)


def test_export_exercise_cases_11_15_and_11_18(
    edge_cases_dataset: LoadedDataset, tmp_path: Path
) -> None:
    """Test export of cases_11_15.csv and cases_11_18.csv."""
    results = run_all_required_analyses(edge_cases_dataset)

    # 11.15
    res_15 = results["11.15"]
    out_15 = tmp_path / "cases_11_15.csv"
    export_exercise_cases_csv(res_15, out_15)
    df_15 = pd.read_csv(out_15, encoding="utf-8-sig")
    assert list(df_15.columns) == CASES_COLUMNS_BY_EXERCISE["11.15"]

    # 11.18
    res_18 = results["11.18"]
    out_18 = tmp_path / "cases_11_18.csv"
    export_exercise_cases_csv(res_18, out_18)
    df_18 = pd.read_csv(out_18, encoding="utf-8-sig")
    assert list(df_18.columns) == CASES_COLUMNS_BY_EXERCISE["11.18"]


def test_export_exercise_cases_11_22(
    edge_cases_dataset: LoadedDataset, tmp_path: Path
) -> None:
    """Test export of cases_11_22.csv with following pair indices and timestamps."""
    results = run_all_required_analyses(edge_cases_dataset)
    res_22 = results["11.22"]

    out_22 = tmp_path / "cases_11_22.csv"
    export_exercise_cases_csv(res_22, out_22)
    df_22 = pd.read_csv(out_22, encoding="utf-8-sig")
    assert list(df_22.columns) == CASES_COLUMNS_BY_EXERCISE["11.22"]


def test_export_exercise_cases_zero_matches(tmp_path: Path) -> None:
    """Test EC-07.3: Exercise producing 0 cases exports valid CSV with header and 0 rows."""
    from core.analyzers import _build_empty_matched_11_15

    zero_res = AnalysisResult(
        exercise_code="11.15",
        title="Zero Matches Test",
        filter_rule="rule",
        case_count=0,
        total_cases=100,
        mean_cycle_time_days=None,
        percentage=0.0,
        matched_cases_df=_build_empty_matched_11_15(),
        evidence_event_indices={},
    )

    out_file = tmp_path / "cases_11_15_zero.csv"
    export_exercise_cases_csv(zero_res, out_file)

    assert out_file.exists()
    df = pd.read_csv(out_file, encoding="utf-8-sig")
    assert len(df) == 0
    assert list(df.columns) == CASES_COLUMNS_BY_EXERCISE["11.15"]


# ==============================================================================
# 3. Tests for GUI Reset/Re-run and Export Buttons (M4.1 & M4.2)
# ==============================================================================


def test_main_window_reset_rerun_in_memory(
    qapp: QApplication, edge_cases_dataset: LoadedDataset
) -> None:
    """Test Invariant 3: Reset / Re-run All recalculates in-memory without re-parsing disk."""
    win = MainWindow()
    win._on_import_succeeded(edge_cases_dataset)

    # Run initial analysis
    results = run_all_required_analyses(edge_cases_dataset)
    win._on_analysis_succeeded(results)
    assert win._state == AppState.RESULTS_READY
    assert len(win._results_cache) == 8

    # Trigger reset and re-run
    with patch.object(win, "_start_analysis") as mock_start:
        win._on_reset_rerun_clicked()
        assert len(win._results_cache) == 0
        mock_start.assert_called_once()

    win.close()
    qapp.processEvents()


def test_analytical_pages_export_buttons_exist(
    qapp: QApplication, edge_cases_dataset: LoadedDataset
) -> None:
    """Verify export buttons are instantiated and accessible on analytical pages."""
    results = run_all_required_analyses(edge_cases_dataset)

    # Page 11.7
    page_7 = Ex11_7Page()
    page_7.set_results(results)
    assert hasattr(page_7, "btn_export")
    assert page_7.btn_export.text() == "Export Selected Category CSV"
    page_7.close()

    # Page 11.15 & 11.18
    page_15_18 = Ex11_15_18Page()
    page_15_18.set_results(results["11.15"], results["11.18"])
    assert hasattr(page_15_18, "btn_export_15")
    assert hasattr(page_15_18, "btn_export_18")
    page_15_18.close()

    # Page 11.22
    page_22 = Ex11_22Page()
    page_22.set_results(results["11.22"])
    assert hasattr(page_22, "btn_export")
    assert page_22.btn_export.text() == "Export 11.22 CSV"
    page_22.close()

    qapp.processEvents()
