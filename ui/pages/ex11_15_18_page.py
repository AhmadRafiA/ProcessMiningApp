"""Exercise 11.15 & 11.18 page: Fraud assessment repetition and resource analysis."""

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
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.exporter import export_exercise_cases_csv, get_canonical_exercise_csv_filename
from core.models import AnalysisResult
from ui.table_models import PandasTableModel


class Ex11_15_18Page(QWidget):
    """Page 3: Exercise 11.15 and 11.18 analytical dual-panel view."""

    request_case_drilldown = Signal(str, str, object)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._res_15: AnalysisResult | None = None
        self._res_18: AnalysisResult | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Title
        title_lbl = QLabel(
            "Exercise 11.15 & 11.18: Pengulangan Penilaian Fraud (W_Assess Potential Fraud)"
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
        rule_title = QLabel("Aturan Filter Semantik Ketat:")
        rule_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #0369A1;")
        rule_layout.addWidget(rule_title)

        rule_desc = QLabel(
            "• Exercise 11.15: Hanya menghitung kejadian aktivitas 'W_Assess Potential Fraud' "
            "berstatus 'complete' (huruf besar/kecil dinormalisasi) dengan frekuensi >= 2 kali.\n"
            "• Exercise 11.18: Memerlukan frekuensi >= 2 kali 'complete' oleh org:resource valid "
            "yang SAMA (resource kosong/NaN/spasi dieliminasi dan tidak dianggap sama)."
        )
        rule_desc.setWordWrap(True)
        rule_desc.setStyleSheet("font-size: 11.5px; color: #0C4A6E;")
        rule_layout.addWidget(rule_desc)
        main_layout.addWidget(rule_box)

        # Splitter for Dual Panels (Left 50%: 11.15 / Right 50%: 11.18)
        splitter = QSplitter()
        splitter.setStyleSheet("QSplitter::handle { background-color: #CBD5E1; width: 3px; }")

        # Left Panel: Exercise 11.15
        p15_widget = QWidget()
        p15_layout = QVBoxLayout(p15_widget)
        p15_layout.setContentsMargins(0, 0, 6, 0)
        p15_layout.setSpacing(8)

        p15_header_layout = QHBoxLayout()
        p15_title = QLabel("Exercise 11.15 (Complete >= 2)")
        p15_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1E293B;")
        p15_header_layout.addWidget(p15_title)

        self.p15_stat_lbl = QLabel("0 cases")
        self.p15_stat_lbl.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #2563EB; background: #DBEAFE; "
            "padding: 2px 8px; border-radius: 4px;"
        )
        p15_header_layout.addWidget(self.p15_stat_lbl)
        p15_header_layout.addStretch()

        btn_drill_15 = QPushButton("Lihat Kasus")
        btn_drill_15.setStyleSheet(
            "background-color: #2563EB; color: #FFFFFF; font-weight: bold; "
            "padding: 4px 10px; border-radius: 4px;"
        )
        btn_drill_15.clicked.connect(self._on_drilldown_15)
        p15_header_layout.addWidget(btn_drill_15)

        self.btn_export_15 = QPushButton("Export CSV")
        self.btn_export_15.setStyleSheet(
            "background-color: #F8FAFC; color: #0F172A; border: 1px solid #CBD5E1; "
            "padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 500;"
        )
        self.btn_export_15.clicked.connect(self._on_export_15)
        p15_header_layout.addWidget(self.btn_export_15)

        p15_layout.addLayout(p15_header_layout)

        self.table_model_15 = PandasTableModel()
        self.table_view_15 = QTableView()
        self.table_view_15.setModel(self.table_model_15)
        self.table_view_15.setAlternatingRowColors(True)
        self.table_view_15.horizontalHeader().setStretchLastSection(True)
        self.table_view_15.doubleClicked.connect(self._on_double_clicked_15)
        p15_layout.addWidget(self.table_view_15)
        splitter.addWidget(p15_widget)

        # Right Panel: Exercise 11.18
        p18_widget = QWidget()
        p18_layout = QVBoxLayout(p18_widget)
        p18_layout.setContentsMargins(6, 0, 0, 0)
        p18_layout.setSpacing(8)

        p18_header_layout = QHBoxLayout()
        p18_title = QLabel("Exercise 11.18 (Resource Sama >= 2)")
        p18_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1E293B;")
        p18_header_layout.addWidget(p18_title)

        self.p18_stat_lbl = QLabel("0 cases")
        self.p18_stat_lbl.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #16A34A; background: #DCFCE7; "
            "padding: 2px 8px; border-radius: 4px;"
        )
        p18_header_layout.addWidget(self.p18_stat_lbl)
        p18_header_layout.addStretch()

        btn_drill_18 = QPushButton("Lihat Kasus")
        btn_drill_18.setStyleSheet(
            "background-color: #16A34A; color: #FFFFFF; font-weight: bold; "
            "padding: 4px 10px; border-radius: 4px;"
        )
        btn_drill_18.clicked.connect(self._on_drilldown_18)
        p18_header_layout.addWidget(btn_drill_18)

        self.btn_export_18 = QPushButton("Export CSV")
        self.btn_export_18.setStyleSheet(
            "background-color: #F8FAFC; color: #0F172A; border: 1px solid #CBD5E1; "
            "padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 500;"
        )
        self.btn_export_18.clicked.connect(self._on_export_18)
        p18_header_layout.addWidget(self.btn_export_18)

        p18_layout.addLayout(p18_header_layout)

        self.table_model_18 = PandasTableModel()
        self.table_view_18 = QTableView()
        self.table_view_18.setModel(self.table_model_18)
        self.table_view_18.setAlternatingRowColors(True)
        self.table_view_18.horizontalHeader().setStretchLastSection(True)
        self.table_view_18.doubleClicked.connect(self._on_double_clicked_18)
        p18_layout.addWidget(self.table_view_18)
        splitter.addWidget(p18_widget)

        splitter.setSizes([600, 600])
        main_layout.addWidget(splitter, stretch=1)

    def set_results(self, res_15: AnalysisResult, res_18: AnalysisResult) -> None:
        """Populate dual panels with 11.15 and 11.18 data."""
        self._res_15 = res_15
        self._res_18 = res_18

        self.p15_stat_lbl.setText(f"{res_15.case_count:,} cases")
        self.table_model_15.set_dataframe(res_15.matched_cases_df)

        self.p18_stat_lbl.setText(f"{res_18.case_count:,} cases")
        self.table_model_18.set_dataframe(res_18.matched_cases_df)

    def clear(self) -> None:
        """Reset both tables and stat badges."""
        self._res_15 = None
        self._res_18 = None
        self.p15_stat_lbl.setText("0 cases")
        self.p18_stat_lbl.setText("0 cases")
        self.table_model_15.set_dataframe(self.table_model_15._df.iloc[0:0])
        self.table_model_18.set_dataframe(self.table_model_18._df.iloc[0:0])

    def _on_drilldown_15(self) -> None:
        selected = self.table_view_15.selectionModel().selectedRows()
        if selected:
            self._trigger_drilldown(self.table_model_15, selected[0].row(), "11.15", self._res_15)

    def _on_double_clicked_15(self, index: QModelIndex) -> None:
        if index.isValid():
            self._trigger_drilldown(self.table_model_15, index.row(), "11.15", self._res_15)

    def _on_drilldown_18(self) -> None:
        selected = self.table_view_18.selectionModel().selectedRows()
        if selected:
            self._trigger_drilldown(self.table_model_18, selected[0].row(), "11.18", self._res_18)

    def _on_double_clicked_18(self, index: QModelIndex) -> None:
        if index.isValid():
            self._trigger_drilldown(self.table_model_18, index.row(), "11.18", self._res_18)

    def _trigger_drilldown(
        self,
        model: PandasTableModel,
        row: int,
        exercise_code: str,
        res: AnalysisResult | None,
    ) -> None:
        df = model.get_dataframe()
        if df.empty or row < 0 or row >= len(df):
            return

        case_id = str(df.iloc[row]["case_id"])
        evidence_indices: list[int] = []
        if res and case_id in res.evidence_event_indices:
            evidence_indices = res.evidence_event_indices[case_id]

        self.request_case_drilldown.emit(case_id, exercise_code, evidence_indices)

    def _on_export_15(self) -> None:
        """Export 11.15 matched cases to CSV."""
        self._export_result(self._res_15, "11.15")

    def _on_export_18(self) -> None:
        """Export 11.18 matched cases to CSV."""
        self._export_result(self._res_18, "11.18")

    def _export_result(self, res: AnalysisResult | None, code: str) -> None:
        if res is None or res.matched_cases_df is None:
            QMessageBox.warning(
                self, "Peringatan", f"Hasil analisis {code} belum tersedia untuk diekspor."
            )
            return

        default_name = get_canonical_exercise_csv_filename(code)
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Ekspor Kasus {code} ke CSV",
            default_name,
            "CSV Files (*.csv);;All Files (*)",
        )
        if not out_path:
            return

        try:
            export_exercise_cases_csv(res, Path(out_path))
            QMessageBox.information(
                self,
                "Ekspor Sukses",
                f"File kasus {code} berhasil disimpan ke:\n{out_path}",
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Gagal Ekspor CSV",
                f"Terjadi kesalahan saat mengekspor kasus {code}:\n\n{e}",
            )

