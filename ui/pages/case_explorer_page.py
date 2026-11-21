"""Case Explorer page (F07) for detailed trace inspection and evidence audit."""

from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.analyzers import extract_case_trace
from core.models import LoadedDataset
from ui.table_models import PandasTableModel


class CaseExplorerPage(QWidget):
    """Case Explorer page allowing trace inspection and evidence highlighting."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dataset: LoadedDataset | None = None
        self._current_case_id: str = ""
        self._current_exercise_code: str = ""
        self._current_highlight_indices: set[int] = set()

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header Title
        title_label = QLabel("Case Explorer (F07) — Audit Bukti Jejak Kasus")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        layout.addWidget(title_label)

        desc_label = QLabel(
            "Periksa jejak kronologis lengkap dari suatu kasus. Baris bukti audit "
            "dari soal Bab 11 ditandai dengan latar belakang kuning dan badge [EVIDENCE]."
        )
        desc_label.setStyleSheet("color: #475569; font-size: 13px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Toolbar: Search Bar + Buttons + Evidence Badge
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)

        lbl_search = QLabel("Case ID:")
        lbl_search.setStyleSheet("font-weight: bold; color: #1E293B;")
        toolbar_layout.addWidget(lbl_search)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Masukkan Case ID (mis. Application_1699990001)...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(
            "background-color: #FFFFFF; color: #0F172A; padding: 6px 12px; "
            "border: 1px solid #CBD5E1; border-radius: 6px; font-size: 13px;"
        )
        self.search_input.returnPressed.connect(self._on_search_clicked)
        toolbar_layout.addWidget(self.search_input, stretch=2)

        self.btn_search = QPushButton("Muat Kasus")
        self.btn_search.setStyleSheet(
            "background-color: #2563EB; color: white; font-weight: bold; padding: 6px 16px; "
            "border-radius: 6px;"
        )
        self.btn_search.clicked.connect(self._on_search_clicked)
        toolbar_layout.addWidget(self.btn_search)

        # Evidence Context Badge
        self.evidence_badge = QLabel("")
        self.evidence_badge.setStyleSheet(
            "background-color: #FEF3C7; color: #92400E; font-weight: bold; padding: 6px 12px; "
            "border: 1px solid #F59E0B; border-radius: 6px; font-size: 12px;"
        )
        self.evidence_badge.setVisible(False)
        toolbar_layout.addWidget(self.evidence_badge, stretch=3)

        self.btn_clear_highlight = QPushButton("Hapus Sorotan")
        self.btn_clear_highlight.setStyleSheet(
            "background-color: #F1F5F9; color: #475569; padding: 6px 12px; "
            "border: 1px solid #CBD5E1; border-radius: 6px; font-size: 12px;"
        )
        self.btn_clear_highlight.setVisible(False)
        self.btn_clear_highlight.clicked.connect(self._on_clear_highlight)
        toolbar_layout.addWidget(self.btn_clear_highlight)

        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        # Case Summary Mini Banner
        self.case_info_banner = QLabel("Belum ada kasus yang dimuat.")
        self.case_info_banner.setStyleSheet(
            "background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; "
            "padding: 8px 14px; font-size: 12px; color: #334155;"
        )
        layout.addWidget(self.case_info_banner)

        # Chronological Trace Table
        self.trace_model = PandasTableModel(pd.DataFrame())
        self.table_view = QTableView()
        self.table_view.setModel(self.trace_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_view.verticalHeader().setDefaultSectionSize(28)
        self.table_view.setStyleSheet(
            "QTableView { background-color: #FFFFFF; color: #0F172A; border: 1px solid #E2E8F0; "
            "border-radius: 6px; font-family: monospace; font-size: 12px; "
            "gridline-color: #E2E8F0; selection-background-color: #2563EB; "
            "selection-color: #FFFFFF; } "
            "QTableView::item { color: #0F172A; } "
            "QTableView::item:selected { background-color: #2563EB; color: #FFFFFF; } "
            "QHeaderView::section { background-color: #F8FAFC; color: #334155; "
            "font-weight: bold; padding: 6px; border: none; border-bottom: 1px solid #CBD5E1; "
            "border-right: 1px solid #E2E8F0; } "
            "QHeaderView::section:vertical { background-color: #F8FAFC; color: #64748B; "
            "border: none; border-bottom: 1px solid #E2E8F0; border-right: 1px solid #CBD5E1; }"
        )
        layout.addWidget(self.table_view, stretch=1)

    def set_dataset(self, dataset: LoadedDataset | None) -> None:
        """Assign active dataset reference."""
        self._dataset = dataset
        self.clear()

    def load_case_with_evidence(
        self,
        case_id: str,
        exercise_code: str = "",
        highlight_indices: set[int] | None = None,
    ) -> None:
        """Load and display the chronological trace of a case with optional evidence highlight."""
        if self._dataset is None:
            QMessageBox.warning(
                self,
                "Dataset Belum Ada",
                "Silakan impor file event log terlebih dahulu sebelum membuka Case Explorer.",
            )
            return

        cid = str(case_id).strip()
        if not cid:
            return

        self._current_case_id = cid
        self._current_exercise_code = exercise_code
        self._current_highlight_indices = set(highlight_indices) if highlight_indices else set()

        self.search_input.setText(cid)

        # Extract complete trace from domain layer
        trace_df = extract_case_trace(
            self._dataset, cid, self._current_highlight_indices
        )

        if trace_df.empty:
            self.trace_model.set_dataframe(pd.DataFrame())
            self.case_info_banner.setText(
                f"Kasus '{cid}' tidak ditemukan di dalam dataset aktif."
            )
            self.evidence_badge.setVisible(False)
            self.btn_clear_highlight.setVisible(False)
            return

        # Update table model
        self.trace_model.set_dataframe(trace_df)

        # Update Evidence Badge
        if self._current_exercise_code and self._current_highlight_indices:
            count_ev = len(self._current_highlight_indices)
            self.evidence_badge.setText(
                f"Bukti {self._current_exercise_code}: {count_ev} event ditandai [EVIDENCE]"
            )
            self.evidence_badge.setVisible(True)
            self.btn_clear_highlight.setVisible(True)
        else:
            self.evidence_badge.setVisible(False)
            self.btn_clear_highlight.setVisible(False)

        # Update Banner Info
        total_events = len(trace_df)
        first_time = trace_df["time:timestamp"].iloc[0]
        last_time = trace_df["time:timestamp"].iloc[-1]

        # Use pre-computed cycle time from CaseSummaryTable (Invariant 3)
        cycle_days = 0.0
        if self._dataset is not None and not self._dataset.case_summary_df.empty:
            summary_row = self._dataset.case_summary_df[
                self._dataset.case_summary_df["case_id"] == cid
            ]
            if not summary_row.empty:
                cycle_days = float(summary_row["cycle_time_days"].iloc[0])
            else:
                first_dt = pd.to_datetime(first_time, utc=True)
                last_dt = pd.to_datetime(last_time, utc=True)
                cycle_days = (last_dt - first_dt).total_seconds() / 86400.0
        else:
            first_dt = pd.to_datetime(first_time, utc=True)
            last_dt = pd.to_datetime(last_time, utc=True)
            cycle_days = (last_dt - first_dt).total_seconds() / 86400.0

        self.case_info_banner.setText(
            f"Case ID: <b>{cid}</b> | Total Events: <b>{total_events:,}</b> | "
            f"Cycle Time: <b>{cycle_days:.2f} hari</b> | "
            f"Start: <b>{first_time}</b> | End: <b>{last_time}</b>"
        )

        # Auto-scroll to first evidence row if present
        if self._current_highlight_indices and "is_evidence" in trace_df.columns:
            evidence_rows = trace_df.index[trace_df["is_evidence"]].tolist()
            if evidence_rows:
                first_row = int(evidence_rows[0])
                model_idx = self.trace_model.index(first_row, 0)
                self.table_view.scrollTo(
                    model_idx, QTableView.ScrollHint.PositionAtCenter
                )
                self.table_view.selectRow(first_row)

    def _on_search_clicked(self) -> None:
        """Handle manual search triggered by user."""
        cid = self.search_input.text().strip()
        if not cid:
            return
        # If searching manually, clear prior exercise highlight context
        self.load_case_with_evidence(cid, exercise_code="", highlight_indices=None)

    def _on_clear_highlight(self) -> None:
        """Remove evidence highlight but keep current case loaded."""
        if self._current_case_id:
            self.load_case_with_evidence(
                self._current_case_id, exercise_code="", highlight_indices=None
            )

    def clear(self) -> None:
        """Reset page to empty state."""
        self._current_case_id = ""
        self._current_exercise_code = ""
        self._current_highlight_indices = set()
        self.search_input.clear()
        self.evidence_badge.setVisible(False)
        self.btn_clear_highlight.setVisible(False)
        self.case_info_banner.setText("Belum ada kasus yang dimuat.")
        self.trace_model.set_dataframe(pd.DataFrame())
