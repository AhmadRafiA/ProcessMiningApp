"""Exercise 11.22 page: Eventually Follows sequence analysis (O_Cancelled -> O_Accepted)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QModelIndex, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.exporter import export_exercise_cases_csv
from core.models import AnalysisResult
from ui.table_models import PandasTableModel


class Ex11_22Page(QWidget):
    """Page 4: Exercise 11.22 sequence analysis and matched traces view."""

    request_case_drilldown = Signal(str, str, object)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._res: AnalysisResult | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Title
        title_lbl = QLabel(
            "Exercise 11.22: Analisis Urutan Aktivitas (O_Cancelled Diikuti O_Accepted)"
        )
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        main_layout.addWidget(title_lbl)

        # Filter Rule Box
        rule_box = QFrame()
        rule_box.setStyleSheet(
            """
            QFrame {
                background-color: #EFF6FF;
                border-left: 4px solid #0284C7;
                border-radius: 4px;
                padding: 10px;
            }
            """
        )
        rule_layout = QVBoxLayout(rule_box)
        rule_layout.setContentsMargins(8, 6, 8, 6)
        rule_title = QLabel("Aturan Filter & Semantik Eventually Follows:")
        rule_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #0369A1;")
        rule_layout.addWidget(rule_title)

        rule_desc = QLabel(
            "Case lolos jika memiliki event 'O_Cancelled' pada posisi i yang diikuti oleh "
            "'O_Accepted' pada posisi j > i dalam satu trace yang telah terurut deterministik "
            "(berdasarkan time:timestamp dan _orig_idx). Kedua aktivitas tidak harus bersebelahan "
            "dan trace tidak harus berakhir di O_Cancelled."
        )
        rule_desc.setWordWrap(True)
        rule_desc.setStyleSheet("font-size: 11.5px; color: #0C4A6E;")
        rule_layout.addWidget(rule_desc)
        main_layout.addWidget(rule_box)

        # Metric KPI Card with Explicit Denominator
        kpi_card = QFrame()
        kpi_card.setStyleSheet(
            """
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
            }
            """
        )
        kpi_layout = QHBoxLayout(kpi_card)
        kpi_layout.setContentsMargins(12, 8, 12, 8)

        v_kpi = QVBoxLayout()
        kpi_title = QLabel("PROPORSI KASUS (EVENTUALLY FOLLOWS)")
        kpi_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748B;")
        v_kpi.addWidget(kpi_title)

        self.kpi_value_lbl = QLabel("0 / 0 cases (0.00%)")
        self.kpi_value_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #2563EB;")
        v_kpi.addWidget(self.kpi_value_lbl)

        self.kpi_sub_lbl = QLabel("Denominator: Total seluruh active cases aktif di dataset.")
        self.kpi_sub_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        v_kpi.addWidget(self.kpi_sub_lbl)
        kpi_layout.addLayout(v_kpi)

        kpi_layout.addStretch()

        self.btn_drilldown = QPushButton("Lihat Rincian Case (Explorer)")
        self.btn_drilldown.setStyleSheet(
            """
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            """
        )
        self.btn_drilldown.clicked.connect(self._on_drilldown_clicked)
        kpi_layout.addWidget(self.btn_drilldown)

        self.btn_export = QPushButton("Export 11.22 CSV")
        self.btn_export.setStyleSheet(
            """
            QPushButton {
                background-color: #F8FAFC;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
            }
            """
        )
        self.btn_export.clicked.connect(self._on_export_clicked)
        kpi_layout.addWidget(self.btn_export)

        main_layout.addWidget(kpi_card)

        # Table View
        table_title = QLabel("Tabel Pasangan Kejadian (O_Cancelled -> O_Accepted)")
        table_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        main_layout.addWidget(table_title)

        self.table_model = PandasTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.doubleClicked.connect(self._on_table_double_clicked)
        main_layout.addWidget(self.table_view, stretch=1)

    def set_results(self, result: AnalysisResult) -> None:
        """Populate KPI card and table with 11.22 analysis results."""
        self._res = result

        pct = result.percentage or 0.0
        self.kpi_value_lbl.setText(
            f"{result.case_count:,} / {result.total_cases:,} cases ({pct:.2f}%)"
        )
        self.table_model.set_dataframe(result.matched_cases_df)

    def clear(self) -> None:
        """Reset page to empty state."""
        self._res = None
        self.kpi_value_lbl.setText("0 / 0 cases (0.00%)")
        self.table_model.set_dataframe(self.table_model._df.iloc[0:0])

    def _on_drilldown_clicked(self) -> None:
        selected = self.table_view.selectionModel().selectedRows()
        if not selected:
            return
        self._trigger_drilldown(selected[0].row())

    def _on_table_double_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        self._trigger_drilldown(index.row())

    def _trigger_drilldown(self, row: int) -> None:
        df = self.table_model.get_dataframe()
        if df.empty or row < 0 or row >= len(df):
            return

        case_id = str(df.iloc[row]["case_id"])
        evidence_indices: list[int] = []
        if self._res and case_id in self._res.evidence_event_indices:
            evidence_indices = self._res.evidence_event_indices[case_id]

        self.request_case_drilldown.emit(case_id, "11.22", evidence_indices)

    def _on_export_clicked(self) -> None:
        """Export 11.22 matched cases to CSV."""
        if self._res is None or self._res.matched_cases_df is None:
            QMessageBox.warning(
                self, "Peringatan", "Hasil analisis 11.22 belum tersedia untuk diekspor."
            )
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Ekspor Kasus 11.22 ke CSV",
            "cases_11_22.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not out_path:
            return

        try:
            export_exercise_cases_csv(self._res, Path(out_path))
            QMessageBox.information(
                self,
                "Ekspor Sukses",
                f"File kasus 11.22 berhasil disimpan ke:\n{out_path}",
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Gagal Ekspor CSV",
                f"Terjadi kesalahan saat mengekspor kasus 11.22:\n\n{e}",
            )

