"""Exercise 11.7 (A–E) analytical page with interactive category selection and drilldown."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QModelIndex, Qt, Signal
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

from core.exporter import export_exercise_cases_csv, get_canonical_exercise_csv_filename
from core.models import AnalysisResult
from ui.table_models import PandasTableModel


class ClickableCard(QFrame):
    """Clickable card that emits clicked signal with its code."""

    clicked = Signal(str)

    def __init__(self, code: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._code = code
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: Any) -> None:  # noqa: N802
        self.clicked.emit(self._code)
        super().mousePressEvent(event)


class Ex11_7Page(QWidget):
    """Page 2: Exercise 11.7 (A–E) analysis and matched cases drilldown."""

    request_case_drilldown = Signal(str, str, object)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._results: dict[str, AnalysisResult] = {}
        self._active_category: str = "11.7 C"
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Title
        title_lbl = QLabel("Exercise 11.7: Analisis Siklus Hidup Kasus & Outcome (A–E)")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        main_layout.addWidget(title_lbl)

        # Filter Rule Box
        self.rule_box = QFrame()
        self.rule_box.setStyleSheet(
            """
            QFrame {
                background-color: #EFF6FF;
                border-left: 4px solid #0284C7;
                border-radius: 4px;
                padding: 10px;
            }
            """
        )
        rule_layout = QVBoxLayout(self.rule_box)
        rule_layout.setContentsMargins(8, 6, 8, 6)
        rule_title = QLabel("Aturan Filter & Definisi Semantik:")
        rule_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #0369A1;")
        rule_layout.addWidget(rule_title)

        self.rule_desc = QLabel(
            "Pilih salah satu kategori kartu (C/D/E) untuk menampilkan daftar kasus yang lolos "
            "dan menelusuri bukti jejaknya di Case Explorer. "
            "Cycle time selalu dihitung dari trace utuh sebelum penyaringan."
        )
        self.rule_desc.setWordWrap(True)
        self.rule_desc.setStyleSheet("font-size: 11.5px; color: #0C4A6E;")
        rule_layout.addWidget(self.rule_desc)
        main_layout.addWidget(self.rule_box)

        # 5 Metric Cards Horizontal Layout
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self.card_a = self._make_card("11.7 A", "Total Unique Cases", "0 cases", "")
        self.card_b = self._make_card("11.7 B", "Mean Cycle Time (All)", "0.00 hari", "")
        self.card_c = self._make_clickable_card(
            "11.7 C", "Successful (O_Accepted)", "0 cases", "0.00 hari"
        )
        self.card_d = self._make_clickable_card(
            "11.7 D", "Unsuccessful (O_Refused)", "0 cases", "0.00 hari"
        )
        self.card_e = self._make_clickable_card(
            "11.7 E", "Canceled (End O_Cancelled)", "0 cases", "0.00 hari"
        )

        cards_layout.addWidget(self.card_a)
        cards_layout.addWidget(self.card_b)
        cards_layout.addWidget(self.card_c)
        cards_layout.addWidget(self.card_d)
        cards_layout.addWidget(self.card_e)
        main_layout.addLayout(cards_layout)

        # Table Section Toolbar
        toolbar_layout = QHBoxLayout()
        self.table_title = QLabel("Daftar Kasus Terpilih: 11.7 C (Successful Cases)")
        self.table_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        toolbar_layout.addWidget(self.table_title)

        toolbar_layout.addStretch()

        self.btn_drilldown = QPushButton("Lihat Rincian Case (Explorer)")
        self.btn_drilldown.setStyleSheet(
            """
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton:disabled {
                background-color: #CBD5E1;
                color: #94A3B8;
            }
            """
        )
        self.btn_drilldown.clicked.connect(self._on_drilldown_clicked)
        toolbar_layout.addWidget(self.btn_drilldown)

        self.btn_export = QPushButton("Export Selected Category CSV")
        self.btn_export.setStyleSheet(
            "QPushButton { background-color: #F8FAFC; color: #0F172A; "
            "border: 1px solid #CBD5E1; padding: 6px 12px; border-radius: 4px; "
            "font-size: 12px; font-weight: 500; } "
            "QPushButton:hover { background-color: #F1F5F9; } "
            "QPushButton:disabled { background-color: #F8FAFC; color: #94A3B8; }"
        )
        self.btn_export.clicked.connect(self._on_export_clicked)
        toolbar_layout.addWidget(self.btn_export)

        main_layout.addLayout(toolbar_layout)

        # Table View
        self.table_model = PandasTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.doubleClicked.connect(self._on_table_double_clicked)
        main_layout.addWidget(self.table_view, stretch=1)

    def _make_card(self, code: str, title: str, main_val: str, sub_val: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 8px;
            }
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        code_lbl = QLabel(code)
        code_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748B;")
        layout.addWidget(code_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #334155;")
        layout.addWidget(title_lbl)

        val_lbl = QLabel(main_val)
        val_lbl.setObjectName(f"val_{code}")
        val_lbl.setStyleSheet("font-size: 17px; font-weight: bold; color: #0F172A;")
        layout.addWidget(val_lbl)

        sub_lbl = QLabel(sub_val)
        sub_lbl.setObjectName(f"sub_{code}")
        sub_lbl.setStyleSheet("font-size: 11px; color: #475569;")
        layout.addWidget(sub_lbl)

        return card

    def _make_clickable_card(
        self, code: str, title: str, main_val: str, sub_val: str
    ) -> ClickableCard:
        card = ClickableCard(code)
        card.setStyleSheet(
            """
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 8px;
            }
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        code_lbl = QLabel(code)
        code_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748B;")
        layout.addWidget(code_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #334155;")
        layout.addWidget(title_lbl)

        val_lbl = QLabel(main_val)
        val_lbl.setObjectName(f"val_{code}")
        val_lbl.setStyleSheet("font-size: 17px; font-weight: bold; color: #0F172A;")
        layout.addWidget(val_lbl)

        sub_lbl = QLabel(sub_val)
        sub_lbl.setObjectName(f"sub_{code}")
        sub_lbl.setStyleSheet("font-size: 11px; color: #475569;")
        layout.addWidget(sub_lbl)

        card.clicked.connect(self._select_category)
        return card

    def _select_category(self, code: str) -> None:
        """Switch active category to C, D, or E and update table."""
        self._active_category = code
        # Update card highlights
        for c, card in [("11.7 C", self.card_c), ("11.7 D", self.card_d), ("11.7 E", self.card_e)]:
            if c == code:
                card.setStyleSheet(
                    """
                    QFrame {
                        background-color: #F0FDF4;
                        border: 2px solid #16A34A;
                        border-radius: 8px;
                        padding: 8px;
                    }
                    """
                )
            else:
                card.setStyleSheet(
                    """
                    QFrame {
                        background-color: #FFFFFF;
                        border: 1px solid #E2E8F0;
                        border-radius: 8px;
                        padding: 8px;
                    }
                    """
                )

        if code in self._results:
            res = self._results[code]
            self.table_title.setText(f"Daftar Kasus Terpilih: {code} — {res.title}")
            self.table_model.set_dataframe(res.matched_cases_df)
            self.rule_desc.setText(f"Aturan {code}: {res.filter_rule}")

    def set_results(self, results: dict[str, AnalysisResult]) -> None:
        """Update 11.7 cards and table view with new analysis results."""
        self._results = results

        for code, card in [
            ("11.7 A", self.card_a),
            ("11.7 B", self.card_b),
            ("11.7 C", self.card_c),
            ("11.7 D", self.card_d),
            ("11.7 E", self.card_e),
        ]:
            if code in results:
                res = results[code]
                val_lbl = card.findChild(QLabel, f"val_{code}")
                sub_lbl = card.findChild(QLabel, f"sub_{code}")

                if code == "11.7 A" and val_lbl:
                    val_lbl.setText(f"{res.case_count:,} cases")
                elif code == "11.7 B" and val_lbl:
                    ct = res.mean_cycle_time_days or 0.0
                    val_lbl.setText(f"{ct:.2f} hari")
                elif val_lbl and sub_lbl:
                    val_lbl.setText(f"{res.case_count:,} cases")
                    ct = res.mean_cycle_time_days or 0.0
                    sub_lbl.setText(f"Mean CT: {ct:.2f} hari")

        self._select_category(self._active_category)

    def clear(self) -> None:
        """Clear results and reset table."""
        self._results.clear()
        self.table_model.set_dataframe(self.table_model._df.iloc[0:0])

    def _on_drilldown_clicked(self) -> None:
        """Handle button click to open selected case in Case Explorer."""
        selected = self.table_view.selectionModel().selectedRows()
        if not selected:
            return
        row = selected[0].row()
        self._trigger_drilldown_for_row(row)

    def _on_table_double_clicked(self, index: QModelIndex) -> None:
        """Handle row double click to open case in Case Explorer."""
        if not index.isValid():
            return
        self._trigger_drilldown_for_row(index.row())

    def _trigger_drilldown_for_row(self, row: int) -> None:
        df = self.table_model.get_dataframe()
        if df.empty or row < 0 or row >= len(df):
            return

        case_id = str(df.iloc[row]["case_id"])
        res = self._results.get(self._active_category)
        evidence_indices: list[int] = []
        if res and case_id in res.evidence_event_indices:
            evidence_indices = res.evidence_event_indices[case_id]

        self.request_case_drilldown.emit(case_id, self._active_category, evidence_indices)

    def _on_export_clicked(self) -> None:
        """Export current category cases to CSV."""
        if self._active_category not in self._results:
            QMessageBox.warning(
                self, "Peringatan", "Hasil analisis belum tersedia untuk diekspor."
            )
            return

        active_res = self._results[self._active_category]
        default_name = get_canonical_exercise_csv_filename(self._active_category)
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Ekspor Kasus {self._active_category} ke CSV",
            default_name,
            "CSV Files (*.csv);;All Files (*)",
        )
        if not out_path:
            return

        try:
            export_exercise_cases_csv(active_res, Path(out_path))
            QMessageBox.information(
                self,
                "Ekspor Sukses",
                f"File kasus berhasil disimpan ke:\n{out_path}",
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Gagal Ekspor CSV",
                f"Terjadi kesalahan saat mengekspor kasus:\n\n{e}",
            )

