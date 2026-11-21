"""Main window shell and thread orchestrator for BPIC17 Event Log Analyzer."""

from __future__ import annotations

import sys
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pm4py
import PySide6
from PySide6.QtCore import QObject, QThread
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.exporter import export_summary_csv
from core.models import AnalysisResult, CSVExportIOError, LoadedDataset
from ui.pages.case_explorer_page import CaseExplorerPage
from ui.pages.ex11_7_page import Ex11_7Page
from ui.pages.ex11_15_18_page import Ex11_15_18Page
from ui.pages.ex11_22_page import Ex11_22Page
from ui.pages.filter_page import FilterBuilderPage
from ui.pages.overview_page import OverviewPage
from ui.theme import apply_light_theme
from ui.workers import AnalysisWorker, ImportWorker


class AppState(StrEnum):
    """Global Application State Machine states."""

    EMPTY_IDLE = "EMPTY_IDLE"
    LOADING_XES = "LOADING_XES"
    DATASET_READY = "DATASET_READY"
    RUNNING_ANALYSIS = "RUNNING_ANALYSIS"
    RESULTS_READY = "RESULTS_READY"
    EXPORTING_CSV = "EXPORTING_CSV"


class AboutDialog(QDialog):
    """Reproducibility and environment diagnostic information dialog."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About — BPIC17 Event Log Analyzer")
        self.setFixedSize(540, 420)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("BPIC17 Event Log Analyzer")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        layout.addWidget(title)

        subtitle = QLabel("Standalone, 100% Offline Process Mining & Analytic Engine (Bab 11)")
        subtitle.setStyleSheet("font-size: 12px; color: #475569;")
        layout.addWidget(subtitle)

        # Diagnostics text
        self.info_text = (
            f"=== Platform & Environment Diagnostics ===\n"
            f"Python Runtime: {sys.version.split()[0]} ({sys.platform})\n"
            f"PM4Py Version: {pm4py.__version__}\n"
            f"Pandas Version: {pd.__version__}\n"
            f"NumPy Version: {np.__version__}\n"
            f"PySide6 (Qt) Version: {PySide6.__version__}\n"
            f"Architecture: 64-bit Offline Engine\n"
            f"Single-Parse In-Memory Cache: Active\n"
            f"Deterministic Sorting (_orig_idx): Enforced\n"
        )

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText(self.info_text)
        text_edit.setFont(QFont("monospace", 11))
        text_edit.setStyleSheet(
            "background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; "
            "border-radius: 6px; padding: 8px;"
        )
        layout.addWidget(text_edit)

        btn_layout = QHBoxLayout()
        btn_copy = QPushButton("Salin Info Lingkungan")
        btn_copy.setStyleSheet(
            "background-color: #2563EB; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 6px;"
        )
        btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_layout.addWidget(btn_copy)

        btn_close = QPushButton("Tutup")
        btn_close.setStyleSheet(
            "background-color: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1; "
            "padding: 6px 14px; border-radius: 6px;"
        )
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def _copy_to_clipboard(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(self.info_text)
            QMessageBox.information(self, "Disalin", "Informasi lingkungan disalin ke clipboard.")


class MainWindow(QMainWindow):
    """Primary UI Shell and worker thread orchestrator."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BPIC17 Event Log Analyzer — Bab 11 Analytics & Case Explorer")
        self.setMinimumSize(1200, 760)
        self.resize(1366, 840)

        # Internal Session State
        self._state: AppState = AppState.EMPTY_IDLE
        self._dataset: LoadedDataset | None = None
        self._results_cache: dict[str, AnalysisResult] = {}

        # Worker & Concurrency management
        self._active_thread: QThread | None = None
        self._active_worker: QObject | None = None

        self._init_ui()
        apply_light_theme(self)
        self._apply_state(AppState.EMPTY_IDLE)

    def _init_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        central_widget.setStyleSheet(
            "QWidget#centralWidget { background-color: #F8FAFC; color: #0F172A; }"
        )
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Header Bar (Height: 56px)
        header_bar = self._create_header_bar()
        root_layout.addWidget(header_bar)

        # 2. Main Body: Sidebar + Stacked Content Pages
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left Sidebar (Width: 230px)
        self.sidebar = self._create_sidebar()
        body_layout.addWidget(self.sidebar)

        # Content Area (QStackedWidget)
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("stackedWidget")
        self.stacked_widget.setStyleSheet(
            "QStackedWidget#stackedWidget { background-color: #F8FAFC; color: #0F172A; }"
        )

        self.page_overview = OverviewPage()
        self.page_11_7 = Ex11_7Page()
        self.page_11_15_18 = Ex11_15_18Page()
        self.page_11_22 = Ex11_22Page()
        self.page_case_explorer = CaseExplorerPage()
        self.page_filter_builder = FilterBuilderPage()

        self.stacked_widget.addWidget(self.page_overview)        # Index 0
        self.stacked_widget.addWidget(self.page_11_7)            # Index 1
        self.stacked_widget.addWidget(self.page_11_15_18)        # Index 2
        self.stacked_widget.addWidget(self.page_11_22)           # Index 3
        self.stacked_widget.addWidget(self.page_case_explorer)   # Index 4
        self.stacked_widget.addWidget(self.page_filter_builder)  # Index 5

        # Wire Drill-Down Navigation Signals to Case Explorer
        self.page_overview.request_case_drilldown.connect(self._handle_drilldown)
        self.page_11_7.request_case_drilldown.connect(self._handle_drilldown)
        self.page_11_15_18.request_case_drilldown.connect(self._handle_drilldown)
        self.page_11_22.request_case_drilldown.connect(self._handle_drilldown)
        self.page_filter_builder.request_case_drilldown.connect(self._handle_drilldown)

        body_layout.addWidget(self.stacked_widget, stretch=1)
        root_layout.addLayout(body_layout, stretch=1)

        # 3. Bottom Status Bar (Height: 32px)
        status_bar = self._create_bottom_status_bar()
        root_layout.addWidget(status_bar)

    def _create_header_bar(self) -> QWidget:
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet(
            "background-color: #FFFFFF; border-bottom: 1px solid #E2E8F0; padding: 0 16px;"
        )
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # Import XES Button
        self.btn_import = QPushButton("Import XES")
        self.btn_import.setStyleSheet(
            "QPushButton { background-color: #2563EB; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 6px; font-size: 13px; } "
            "QPushButton:hover { background-color: #1D4ED8; } "
            "QPushButton:disabled { background-color: #E2E8F0; color: #94A3B8; }"
        )
        self.btn_import.clicked.connect(self._on_import_clicked)
        layout.addWidget(self.btn_import)

        # File Label
        self.lbl_file = QLabel("File: Tidak ada dataset")
        self.lbl_file.setStyleSheet("color: #334155; font-size: 13px; font-weight: 500;")
        layout.addWidget(self.lbl_file)

        # Status Badge
        self.badge_status = QLabel("NO DATASET")
        self.badge_status.setStyleSheet(
            "background-color: #F1F5F9; color: #475569; font-weight: bold; "
            "padding: 4px 10px; border-radius: 4px; font-size: 11px;"
        )
        layout.addWidget(self.badge_status)

        layout.addStretch()

        # Action Buttons
        self.btn_run_analysis = QPushButton("Run Analysis")
        self.btn_run_analysis.setStyleSheet(
            "QPushButton { background-color: #059669; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 6px; font-size: 13px; } "
            "QPushButton:hover { background-color: #047857; } "
            "QPushButton:disabled { background-color: #E2E8F0; color: #94A3B8; }"
        )
        self.btn_run_analysis.clicked.connect(self._on_run_analysis_clicked)
        layout.addWidget(self.btn_run_analysis)

        self.btn_reset_rerun = QPushButton("Reset / Re-run All")
        self.btn_reset_rerun.setStyleSheet(
            "QPushButton { background-color: #F8FAFC; color: #0F172A; "
            "border: 1px solid #CBD5E1; padding: 8px 14px; border-radius: 6px; font-size: 13px; } "
            "QPushButton:hover { background-color: #F1F5F9; } "
            "QPushButton:disabled { background-color: #F8FAFC; color: #94A3B8; "
            "border-color: #E2E8F0; }"
        )
        self.btn_reset_rerun.clicked.connect(self._on_reset_rerun_clicked)
        layout.addWidget(self.btn_reset_rerun)

        self.btn_export_summary = QPushButton("Export Summary CSV")
        self.btn_export_summary.setStyleSheet(
            "QPushButton { background-color: #F8FAFC; color: #0F172A; "
            "border: 1px solid #CBD5E1; padding: 8px 14px; border-radius: 6px; font-size: 13px; } "
            "QPushButton:hover { background-color: #F1F5F9; } "
            "QPushButton:disabled { background-color: #F8FAFC; color: #94A3B8; "
            "border-color: #E2E8F0; }"
        )
        self.btn_export_summary.clicked.connect(self._on_export_summary_clicked)
        layout.addWidget(self.btn_export_summary)

        self.btn_about = QPushButton("About")
        self.btn_about.setStyleSheet(
            "QPushButton { background-color: #F8FAFC; color: #475569; "
            "border: 1px solid #CBD5E1; padding: 8px 12px; border-radius: 6px; font-size: 13px; } "
            "QPushButton:hover { background-color: #F1F5F9; }"
        )
        self.btn_about.clicked.connect(self._on_about_clicked)
        layout.addWidget(self.btn_about)

        return header

    def _create_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet(
            "background-color: #F8FAFC; border-right: 1px solid #E2E8F0; padding: 12px 8px;"
        )
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(6)

        nav_title = QLabel("NAVIGASI")
        nav_title.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #94A3B8; "
            "padding-left: 8px; margin-bottom: 4px;"
        )
        layout.addWidget(nav_title)

        self.nav_buttons: list[QPushButton] = []
        nav_items = [
            ("(1) Overview", 0),
            ("(2) Exercise 11.7 (A–E)", 1),
            ("(3) Ex 11.15 & 11.18", 2),
            ("(4) Exercise 11.22", 3),
            ("(5) Case Explorer", 4),
            ("(6) Filter Builder (Disco)", 5),
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding-left: 12px; border-radius: 6px; "
                "font-size: 13px; color: #334155; border: none; font-weight: 500; } "
                "QPushButton:hover { background-color: #E2E8F0; color: #0F172A; } "
                "QPushButton:checked { background-color: #2563EB; color: white; "
                "font-weight: bold; }"
            )
            btn.clicked.connect(lambda checked, idx=index: self._navigate_to_page(idx))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Check first nav item initially
        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)

        return sidebar

    def _create_bottom_status_bar(self) -> QWidget:
        status_bar = QFrame()
        status_bar.setFixedHeight(32)
        status_bar.setStyleSheet(
            "background-color: #FFFFFF; border-top: 1px solid #E2E8F0; padding: 0 16px;"
        )
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        self.lbl_status = QLabel("Status: Ready (Belum ada dataset)")
        self.lbl_status.setStyleSheet("font-size: 12px; color: #475569;")
        layout.addWidget(self.lbl_status, stretch=2)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #E2E8F0; border-radius: 6px; } "
            "QProgressBar::chunk { background-color: #2563EB; border-radius: 6px; }"
        )
        layout.addWidget(self.progress_bar, stretch=3)

        self.lbl_quick_stats = QLabel("Cases: - | Events: -")
        self.lbl_quick_stats.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 500;")
        layout.addWidget(self.lbl_quick_stats)

        return status_bar

    def _navigate_to_page(self, index: int) -> None:
        """Switch active page in stacked widget and update sidebar selection."""
        self.stacked_widget.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def _apply_state(self, new_state: AppState) -> None:
        """Enforce single-active-worker and button states per state machine."""
        self._state = new_state

        if new_state == AppState.EMPTY_IDLE:
            self.badge_status.setText("NO DATASET")
            self.badge_status.setStyleSheet(
                "background-color: #F1F5F9; color: #475569; font-weight: bold; "
                "padding: 4px 10px; border-radius: 4px; font-size: 11px;"
            )
            self.btn_import.setEnabled(True)
            self.btn_run_analysis.setEnabled(False)
            self.btn_reset_rerun.setEnabled(False)
            self.btn_export_summary.setEnabled(False)
            self.progress_bar.setValue(0)
            self.lbl_status.setText("Status: Ready (Belum ada dataset)")
            self.lbl_quick_stats.setText("Cases: - | Events: -")

        elif new_state == AppState.LOADING_XES:
            self.badge_status.setText("LOADING XES...")
            self.badge_status.setStyleSheet(
                "background-color: #EFF6FF; color: #1D4ED8; font-weight: bold; "
                "padding: 4px 10px; border-radius: 4px; font-size: 11px;"
            )
            self.btn_import.setEnabled(False)
            self.btn_run_analysis.setEnabled(False)
            self.btn_reset_rerun.setEnabled(False)
            self.btn_export_summary.setEnabled(False)

        elif new_state == AppState.DATASET_READY:
            self.badge_status.setText("READY")
            self.badge_status.setStyleSheet(
                "background-color: #DCFCE7; color: #15803D; font-weight: bold; "
                "padding: 4px 10px; border-radius: 4px; font-size: 11px;"
            )
            self.btn_import.setEnabled(True)
            self.btn_run_analysis.setEnabled(True)
            self.btn_reset_rerun.setEnabled(True)
            self.btn_export_summary.setEnabled(False)
            self.progress_bar.setValue(100)
            self.lbl_status.setText("Status: Dataset berhasil dimuat. Siap dianalisis.")

        elif new_state == AppState.RUNNING_ANALYSIS:
            self.badge_status.setText("RUNNING...")
            self.badge_status.setStyleSheet(
                "background-color: #EFF6FF; color: #1D4ED8; font-weight: bold; "
                "padding: 4px 10px; border-radius: 4px; font-size: 11px;"
            )
            self.btn_import.setEnabled(False)
            self.btn_run_analysis.setEnabled(False)
            self.btn_reset_rerun.setEnabled(False)
            self.btn_export_summary.setEnabled(False)

        elif new_state == AppState.RESULTS_READY:
            self.badge_status.setText("COMPLETED")
            self.badge_status.setStyleSheet(
                "background-color: #DCFCE7; color: #15803D; font-weight: bold; "
                "padding: 4px 10px; border-radius: 4px; font-size: 11px;"
            )
            self.btn_import.setEnabled(True)
            self.btn_run_analysis.setEnabled(True)
            self.btn_reset_rerun.setEnabled(True)
            self.btn_export_summary.setEnabled(True)
            self.progress_bar.setValue(100)
            self.lbl_status.setText("Status: Analisis Bab 11 selesai. Hasil tersimpan di memori.")

    def _on_import_clicked(self) -> None:
        """Handle Import XES button click with file picker dialog."""
        if self._active_thread is not None and self._active_thread.isRunning():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih File Event Log BPIC17",
            "",
            "XES Files (*.xes *.xes.gz);;All Files (*)",
        )
        if not file_path:
            return

        self._start_import(file_path)

    def _start_import(self, file_path: str) -> None:
        """Start asynchronous import in background QThread."""
        self._apply_state(AppState.LOADING_XES)
        self.lbl_file.setText(f"File: {Path(file_path).name}")

        self._active_thread = QThread()
        self._active_worker = ImportWorker(file_path)
        self._active_worker.moveToThread(self._active_thread)

        # Connect signals
        self._active_thread.started.connect(self._active_worker.run)
        self._active_worker.progress_updated.connect(self._on_worker_progress)
        self._active_worker.import_succeeded.connect(self._on_import_succeeded)
        self._active_worker.import_failed.connect(self._on_import_failed)

        # Thread lifecycle cleanup
        self._active_worker.import_succeeded.connect(self._active_thread.quit)
        self._active_worker.import_failed.connect(self._active_thread.quit)
        self._active_thread.finished.connect(self._cleanup_active_thread)

        self._active_thread.start()

    def _on_worker_progress(self, percent: int, msg: str) -> None:
        self.progress_bar.setValue(percent)
        self.lbl_status.setText(f"Status: {msg}")

    def _on_import_succeeded(self, dataset: LoadedDataset) -> None:
        """Handle successful import: update session state and populate Overview."""
        self._dataset = dataset
        self._results_cache.clear()

        # Populate Overview and Case Explorer
        self.page_overview.load_dataset(dataset)
        self.page_case_explorer.set_dataset(dataset)
        self.page_filter_builder.set_dataset(dataset)

        # Reset other pages
        self.page_11_7.clear()
        self.page_11_15_18.clear()
        self.page_11_22.clear()

        # Update status bar stats
        ov = dataset.overview
        self.lbl_quick_stats.setText(f"Cases: {ov.total_cases:,} | Events: {ov.total_events:,}")

        # Navigate to Overview page
        self._navigate_to_page(0)
        self._apply_state(AppState.DATASET_READY)

    def _on_import_failed(self, err_code: str, user_msg: str) -> None:
        """Handle import failure with friendly error dialog."""
        QMessageBox.critical(
            self,
            f"Gagal Mengimpor ({err_code})",
            f"Terjadi kesalahan saat memproses file event log:\n\n{user_msg}",
        )
        if self._dataset is not None:
            self._apply_state(AppState.DATASET_READY)
        else:
            self._apply_state(AppState.EMPTY_IDLE)

    def _on_run_analysis_clicked(self) -> None:
        """Run analysis on active dataset."""
        if self._dataset is None:
            QMessageBox.warning(self, "Peringatan", "Silakan impor dataset terlebih dahulu.")
            return

        self._start_analysis()

    def _on_reset_rerun_clicked(self) -> None:
        """Reset analysis cache and re-run on in-memory dataset without re-parsing disk."""
        if self._dataset is None:
            return

        self._results_cache.clear()
        self.page_11_7.clear()
        self.page_11_15_18.clear()
        self.page_11_22.clear()
        self.page_filter_builder.set_dataset(self._dataset)
        self._start_analysis()

    def _start_analysis(self) -> None:
        """Start asynchronous analytics computation in background QThread."""
        if self._dataset is None:
            return
        if self._active_thread is not None and self._active_thread.isRunning():
            return

        self._apply_state(AppState.RUNNING_ANALYSIS)

        self._active_thread = QThread()
        self._active_worker = AnalysisWorker(self._dataset)
        self._active_worker.moveToThread(self._active_thread)

        self._active_thread.started.connect(self._active_worker.run)
        self._active_worker.progress_updated.connect(self._on_worker_progress)
        self._active_worker.analysis_succeeded.connect(self._on_analysis_succeeded)
        self._active_worker.analysis_failed.connect(self._on_analysis_failed)

        self._active_worker.analysis_succeeded.connect(self._active_thread.quit)
        self._active_worker.analysis_failed.connect(self._active_thread.quit)
        self._active_thread.finished.connect(self._cleanup_active_thread)

        self._active_thread.start()

    def _on_analysis_succeeded(self, results: dict[str, AnalysisResult]) -> None:
        """Handle successful analysis: update cache and analytical pages."""
        self._results_cache = results

        self.page_11_7.set_results(results)
        if "11.15" in results and "11.18" in results:
            self.page_11_15_18.set_results(results["11.15"], results["11.18"])
        if "11.22" in results:
            self.page_11_22.set_results(results["11.22"])

        self._apply_state(AppState.RESULTS_READY)

    def _on_analysis_failed(self, err_code: str, user_msg: str) -> None:
        """Handle analysis failure."""
        QMessageBox.critical(
            self,
            f"Gagal Analisis ({err_code})",
            f"Terjadi kesalahan saat menghitung analisis Bab 11:\n\n{user_msg}",
        )
        self._apply_state(AppState.DATASET_READY)

    def _handle_drilldown(
        self, case_id: str, exercise_code: str, evidence_indices: Any
    ) -> None:
        """Route 1-click drilldown from analytical pages directly to Case Explorer."""
        self._navigate_to_page(4)  # Switch to Case Explorer
        indices_set: set[int] | None = None
        if evidence_indices:
            indices_set = set(evidence_indices)
        self.page_case_explorer.load_case_with_evidence(case_id, exercise_code, indices_set)

    def _on_export_summary_clicked(self) -> None:
        """Trigger summary CSV export (delegated to Stage 4 exporter)."""
        if not self._results_cache:
            QMessageBox.warning(
                self,
                "Belum Ada Hasil",
                "Silakan jalankan analisis terlebih dahulu sebelum mengekspor CSV.",
            )
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Ringkasan Hasil CSV",
            "summary_results.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not out_path:
            return

        try:
            dataset_fn = (
                self._dataset.overview.dataset_filename if self._dataset else "dataset.xes"
            )
            export_summary_csv(self._results_cache, dataset_fn, Path(out_path))
            QMessageBox.information(
                self,
                "Ekspor Sukses",
                f"File ringkasan berhasil disimpan ke:\n{out_path}",
            )
        except CSVExportIOError as err:
            QMessageBox.critical(
                self,
                f"Gagal Ekspor CSV ({err.code})",
                f"{err.user_message}\n\nDetail: {err.detail}",
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Gagal Ekspor CSV",
                f"Gagal menyimpan file CSV:\n\n{e}",
            )

    def _on_about_clicked(self) -> None:
        """Show About / Environment diagnostics dialog."""
        dlg = AboutDialog(self)
        dlg.exec()

    def _cleanup_active_thread(self) -> None:
        """Clean up finished worker and thread."""
        if self._active_worker:
            self._active_worker.deleteLater()
            self._active_worker = None
        if self._active_thread:
            self._active_thread.deleteLater()
            self._active_thread = None

    def closeEvent(self, event: Any) -> None:
        """Ensure clean thread termination on application window close."""
        if self._active_worker is not None and hasattr(self._active_worker, "cancel"):
            self._active_worker.cancel()
        if self._active_thread is not None and self._active_thread.isRunning():
            self._active_thread.requestInterruption()
            self._active_thread.quit()
            self._active_thread.wait(5000)
        event.accept()
