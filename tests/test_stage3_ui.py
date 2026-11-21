"""Unit and integration tests for Stage 3: Client Data Layer, Thread Workers, & Primary UI Shell."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication

# Set headless Qt offscreen platform before creating QApplication
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from core.models import AnalysisResult, LoadedDataset
from ui.main_window import AppState, MainWindow
from ui.pages.case_explorer_page import CaseExplorerPage
from ui.pages.ex11_7_page import Ex11_7Page
from ui.pages.ex11_15_18_page import Ex11_15_18Page
from ui.pages.ex11_22_page import Ex11_22Page
from ui.pages.overview_page import OverviewPage
from ui.table_models import PandasTableModel
from ui.workers import AnalysisWorker, ImportWorker


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Provide a headless QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    assert isinstance(app, QApplication)
    return app


@pytest.fixture
def sample_dataset(edge_cases_dataset: LoadedDataset) -> LoadedDataset:
    """Fixture providing a populated LoadedDataset."""
    return edge_cases_dataset


# ==============================================================================
# 1. Tests for PandasTableModel (M3.1)
# ==============================================================================


def test_pandas_table_model_empty(qapp: QApplication) -> None:
    """Test model behaviors on an empty DataFrame."""
    model = PandasTableModel(pd.DataFrame())
    assert model.rowCount() == 0
    assert model.columnCount() == 0
    assert model.headerData(0, Qt.Orientation.Horizontal) is None
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) is None


def test_pandas_table_model_formatting_and_alignment(qapp: QApplication) -> None:
    """Test number, percentage, duration, and timestamp formatting in PandasTableModel."""
    df = pd.DataFrame(
        {
            "case_id": ["Case_01", "Case_02"],
            "event_count": [1500, 32000],
            "cycle_time_days": [3.456, 0.0],
            "percentage": [12.345, 99.9],
            "time:timestamp": pd.to_datetime(
                ["2016-01-01 10:00:00+00:00", "2016-01-02 12:30:00+00:00"]
            ),
            "is_evidence": [True, False],
        }
    )
    model = PandasTableModel(df)

    assert model.rowCount() == 2
    assert model.columnCount() == 6

    # Header display
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Case ID"
    assert model.headerData(1, Qt.Orientation.Horizontal) == "Events"
    assert model.headerData(2, Qt.Orientation.Horizontal) == "Cycle Time"

    # Thousands separator
    idx_events = model.index(1, 1)
    assert model.data(idx_events, Qt.ItemDataRole.DisplayRole) == "32,000"

    # Cycle time with 'hari'
    idx_dur = model.index(0, 2)
    assert model.data(idx_dur, Qt.ItemDataRole.DisplayRole) == "3.46 hari"

    # Percentage format
    idx_pct = model.index(0, 3)
    assert model.data(idx_pct, Qt.ItemDataRole.DisplayRole) == "12.35%"

    # Timestamp UTC
    idx_ts = model.index(0, 4)
    assert "2016-01-01 10:00:00 UTC" in str(model.data(idx_ts, Qt.ItemDataRole.DisplayRole))

    # Evidence row styling: Row 0 is evidence (True) -> yellow background & bold font
    idx_ev_cell = model.index(0, 0)
    bg_color = model.data(idx_ev_cell, Qt.ItemDataRole.BackgroundRole)
    fg_color = model.data(idx_ev_cell, Qt.ItemDataRole.ForegroundRole)
    font = model.data(idx_ev_cell, Qt.ItemDataRole.FontRole)

    assert isinstance(bg_color, QColor)
    assert bg_color.name().upper() == "#FEF08A"
    assert isinstance(fg_color, QColor)
    assert fg_color.name().upper() == "#713F12"
    assert isinstance(font, QFont)
    assert font.bold() is True

    # Row 1 is NOT evidence -> background is None (allows alternating rows)
    # Foreground must return explicit high-contrast slate color
    idx_non_ev = model.index(1, 0)
    assert model.data(idx_non_ev, Qt.ItemDataRole.BackgroundRole) is None
    assert isinstance(model.data(idx_non_ev, Qt.ItemDataRole.ForegroundRole), QColor)
    assert model.data(idx_non_ev, Qt.ItemDataRole.ForegroundRole).name().upper() == "#0F172A"


def test_pandas_table_model_set_dataframe(qapp: QApplication) -> None:
    """Test atomic model reset when set_dataframe is called."""
    model = PandasTableModel(pd.DataFrame({"A": [1, 2]}))
    assert model.rowCount() == 2

    new_df = pd.DataFrame({"X": [10, 20, 30, 40]})
    model.set_dataframe(new_df)
    assert model.rowCount() == 4
    assert model.columnCount() == 1
    assert model.get_dataframe().equals(new_df)


# ==============================================================================
# 2. Tests for Worker Threads (M3.1)
# ==============================================================================


def test_import_worker_success(edge_cases_dataset: LoadedDataset, tmp_path: Path) -> None:
    """Test ImportWorker execution happy path."""
    import pm4py

    xes_path = tmp_path / "worker_test.xes"
    pm4py.write_xes(edge_cases_dataset.raw_df, str(xes_path))

    worker = ImportWorker(str(xes_path))
    progress_records: list[tuple[int, str]] = []
    success_records: list[LoadedDataset] = []
    failure_records: list[tuple[str, str]] = []

    worker.progress_updated.connect(lambda p, m: progress_records.append((p, m)))
    worker.import_succeeded.connect(lambda ds: success_records.append(ds))
    worker.import_failed.connect(lambda c, m: failure_records.append((c, m)))

    worker.run()

    assert len(failure_records) == 0
    assert len(success_records) == 1
    assert len(progress_records) > 0
    assert success_records[0].overview.total_cases > 0


def test_import_worker_file_not_found(tmp_path: Path) -> None:
    """Test ImportWorker failure on missing file."""
    missing_file = tmp_path / "non_existent.xes"
    worker = ImportWorker(str(missing_file))

    success_records: list[LoadedDataset] = []
    failure_records: list[tuple[str, str]] = []

    worker.import_succeeded.connect(lambda ds: success_records.append(ds))
    worker.import_failed.connect(lambda c, m: failure_records.append((c, m)))

    worker.run()

    assert len(success_records) == 0
    assert len(failure_records) == 1
    assert failure_records[0][0] == "ERR_XES_NOT_FOUND"


def test_import_worker_cancellation(tmp_path: Path) -> None:
    """Test cancellation flag on ImportWorker."""
    worker = ImportWorker(str(tmp_path / "dummy.xes"))
    assert worker._is_cancelled is False
    worker.cancel()
    assert worker._is_cancelled is True


def test_analysis_worker_success(sample_dataset: LoadedDataset) -> None:
    """Test AnalysisWorker execution happy path."""
    worker = AnalysisWorker(sample_dataset)

    progress_records: list[tuple[int, str]] = []
    success_records: list[dict[str, AnalysisResult]] = []
    failure_records: list[tuple[str, str]] = []

    worker.progress_updated.connect(lambda p, m: progress_records.append((p, m)))
    worker.analysis_succeeded.connect(lambda r: success_records.append(r))
    worker.analysis_failed.connect(lambda c, m: failure_records.append((c, m)))

    worker.run()

    assert len(failure_records) == 0
    assert len(success_records) == 1
    results = success_records[0]

    # Verify all 8 required exercise keys exist
    expected_keys = {"11.7 A", "11.7 B", "11.7 C", "11.7 D", "11.7 E", "11.15", "11.18", "11.22"}
    assert set(results.keys()) == expected_keys
    assert len(progress_records) >= 5


# ==============================================================================
# 3. Tests for UI Pages (M3.2 & M3.3)
# ==============================================================================


def test_overview_page_load_and_clear(qapp: QApplication, sample_dataset: LoadedDataset) -> None:
    """Test OverviewPage population and resetting."""
    page = OverviewPage()
    page.load_dataset(sample_dataset)

    assert page.activity_table_model.rowCount() > 0
    assert page.case_summary_table_model.rowCount() > 0

    page.clear()
    assert page.activity_table_model.rowCount() == 0
    assert page.case_summary_table_model.rowCount() == 0
    page.close()
    qapp.processEvents()


def test_ex11_7_page_category_switching(
    qapp: QApplication, sample_dataset: LoadedDataset
) -> None:
    """Test category switching (C, D, E) on Ex11_7Page."""
    from core.analyzers import analyze_exercise_11_7

    results = analyze_exercise_11_7(sample_dataset)
    page = Ex11_7Page()
    page.set_results(results)

    # Initial active category is C
    assert page._active_category == "11.7 C"
    assert page.table_model.rowCount() >= 0

    # Switch to D
    page._select_category("11.7 D")
    assert page._active_category == "11.7 D"

    # Switch to E
    page._select_category("11.7 E")
    assert page._active_category == "11.7 E"
    page.close()
    qapp.processEvents()


def test_ex11_15_18_page_set_results(
    qapp: QApplication, sample_dataset: LoadedDataset
) -> None:
    """Test Ex11_15_18Page dual panel population."""
    from core.analyzers import analyze_exercise_11_15, analyze_exercise_11_18

    res_15 = analyze_exercise_11_15(sample_dataset)
    res_18 = analyze_exercise_11_18(sample_dataset)

    page = Ex11_15_18Page()
    page.set_results(res_15, res_18)

    assert page.table_model_15.rowCount() == res_15.case_count
    assert page.table_model_18.rowCount() == res_18.case_count

    page.clear()
    assert page.table_model_15.rowCount() == 0
    assert page.table_model_18.rowCount() == 0
    page.close()
    qapp.processEvents()


def test_ex11_22_page_set_results(
    qapp: QApplication, sample_dataset: LoadedDataset
) -> None:
    """Test Ex11_22Page population and denominator display."""
    from core.analyzers import analyze_exercise_11_22

    res_22 = analyze_exercise_11_22(sample_dataset)
    page = Ex11_22Page()
    page.set_results(res_22)

    assert page.table_model.rowCount() == res_22.case_count
    assert f"{res_22.case_count:,}" in page.kpi_value_lbl.text()

    page.clear()
    assert page.table_model.rowCount() == 0
    page.close()
    qapp.processEvents()


def test_case_explorer_page_evidence_highlight(
    qapp: QApplication, sample_dataset: LoadedDataset
) -> None:
    """Test CaseExplorerPage loading trace and evidence highlight badges."""
    page = CaseExplorerPage()
    page.show()
    page.set_dataset(sample_dataset)

    first_case = sample_dataset.case_summary_df["case_id"].iloc[0]

    # Load without evidence
    page.load_case_with_evidence(first_case)
    assert page.trace_model.rowCount() > 0
    assert not page.evidence_badge.isVisible()

    # Load with evidence indices
    evidence_indices = {0, 1}
    page.load_case_with_evidence(
        first_case, exercise_code="11.22", highlight_indices=evidence_indices
    )
    assert page.evidence_badge.isVisible()
    assert "11.22" in page.evidence_badge.text()

    # Clear highlight
    page._on_clear_highlight()
    assert not page.evidence_badge.isVisible()
    page.close()
    qapp.processEvents()


# ==============================================================================
# 4. Tests for MainWindow Shell & State Machine (M3.2)
# ==============================================================================


def test_main_window_initial_state(qapp: QApplication) -> None:
    """Test initial state and button guards on MainWindow."""
    win = MainWindow()

    assert win._state == AppState.EMPTY_IDLE
    assert win.btn_import.isEnabled() is True
    assert win.btn_run_analysis.isEnabled() is False
    assert win.btn_reset_rerun.isEnabled() is False
    assert win.btn_export_summary.isEnabled() is False
    assert win.badge_status.text() == "NO DATASET"

    win.close()
    qapp.processEvents()


def test_main_window_state_transitions(qapp: QApplication, sample_dataset: LoadedDataset) -> None:
    """Test state machine transitions and button enabling in MainWindow."""
    from core.analyzers import run_all_required_analyses

    win = MainWindow()

    # Transition to DATASET_READY via _on_import_succeeded
    win._on_import_succeeded(sample_dataset)
    assert win._state == AppState.DATASET_READY
    assert win.btn_import.isEnabled() is True
    assert win.btn_run_analysis.isEnabled() is True
    assert win.btn_reset_rerun.isEnabled() is True
    assert win.btn_export_summary.isEnabled() is False
    assert win.badge_status.text() == "READY"
    assert win.page_overview.case_summary_table_model.rowCount() > 0

    # Transition to RESULTS_READY via _on_analysis_succeeded
    results = run_all_required_analyses(sample_dataset)
    win._on_analysis_succeeded(results)
    assert win._state == AppState.RESULTS_READY  # type: ignore[comparison-overlap]
    assert win.btn_export_summary.isEnabled() is True
    assert win.badge_status.text() == "COMPLETED"
    assert win.page_11_7.table_model.rowCount() >= 0

    win.close()
    qapp.processEvents()


def test_main_window_drilldown_routing(qapp: QApplication, sample_dataset: LoadedDataset) -> None:
    """Test 1-click drilldown navigation from analytical page to Case Explorer."""
    from core.analyzers import run_all_required_analyses

    win = MainWindow()
    win._on_import_succeeded(sample_dataset)
    results = run_all_required_analyses(sample_dataset)
    win._on_analysis_succeeded(results)

    first_case = sample_dataset.case_summary_df["case_id"].iloc[0]

    # Emit drilldown from 11.7 page
    win.page_11_7.request_case_drilldown.emit(first_case, "11.7 C", [0, 1])

    # Check that stacked widget navigated to index 4 (Case Explorer)
    assert win.stacked_widget.currentIndex() == 4
    assert win.page_case_explorer._current_case_id == first_case
    assert win.page_case_explorer._current_exercise_code == "11.7 C"

    win.close()
    qapp.processEvents()
