"""FilterBuilderPage for interactive Disco-style stacked filtering."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.exporter import export_filtered_cases_csv
from core.filters import BaseFilterRule, FilterStepSummary, apply_filter_stack
from core.models import LoadedDataset
from ui.dialogs.filter_dialog import AddFilterDialog
from ui.table_models import PandasTableModel


class FilterCard(QFrame):
    """Visual card for an individual rule in the filter stack."""

    rule_toggled = Signal(int, bool)
    rule_deleted = Signal(int)

    def __init__(
        self,
        rule_idx: int,
        rule: BaseFilterRule,
        summary: FilterStepSummary | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.rule_idx = rule_idx
        self.rule = rule

        self.setStyleSheet(
            "FilterCard { background-color: #FFFFFF; border: 1px solid #CBD5E1; "
            "border-radius: 6px; padding: 6px; } "
            "FilterCard:hover { border-color: #94A3B8; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Top row: Checkbox, Type Badge, Delete Button
        top_row = QHBoxLayout()

        self.chk_enabled = QCheckBox()
        self.chk_enabled.setChecked(rule.is_enabled)
        self.chk_enabled.toggled.connect(self._on_toggled)
        top_row.addWidget(self.chk_enabled)

        badge_type = QLabel(f"#{rule_idx + 1} {rule.filter_type.value}")
        badge_type.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #0284C7; "
            "background-color: #E0F2FE; padding: 2px 6px; border-radius: 4px;"
        )
        top_row.addWidget(badge_type)
        top_row.addStretch()

        btn_delete = QPushButton("✕")
        btn_delete.setToolTip("Hapus filter ini")
        btn_delete.setFixedSize(20, 20)
        btn_delete.setStyleSheet(
            "QPushButton { background: transparent; color: #94A3B8; "
            "font-weight: bold; border: none; } "
            "QPushButton:hover { color: #DC2626; background: #FEE2E2; border-radius: 10px; }"
        )
        btn_delete.clicked.connect(lambda: self.rule_deleted.emit(self.rule_idx))
        top_row.addWidget(btn_delete)
        layout.addLayout(top_row)

        # Rule Description
        desc_lbl = QLabel(rule.describe())
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(
            "font-size: 12px; color: #0F172A; font-weight: 500;"
            if rule.is_enabled
            else "font-size: 12px; color: #94A3B8; font-style: italic;"
        )
        layout.addWidget(desc_lbl)

        # Impact / Step Summary
        if summary is not None:
            pct_str = f"{summary.case_retention_pct:.2f}%"
            stat_lbl = QLabel(
                f"Lolos: {summary.cases_after:,} kasus ({pct_str})"
                if rule.is_enabled
                else "Filter nonaktif (dilewati)"
            )
            stat_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
            layout.addWidget(stat_lbl)

    def _on_toggled(self, checked: bool) -> None:
        self.rule.is_enabled = checked
        self.rule_toggled.emit(self.rule_idx, checked)


class FilterBuilderPage(QWidget):
    """Full-featured interactive Disco-style filter builder page."""

    request_case_drilldown = Signal(str, str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dataset: LoadedDataset | None = None
        self._filtered_dataset: LoadedDataset | None = None
        self._rules: list[BaseFilterRule] = []
        self._step_summaries: list[FilterStepSummary] = []

        self._init_ui()

    def set_dataset(self, dataset: LoadedDataset | None) -> None:
        """Assign active dataset reference and reset filter stack."""
        self._dataset = dataset
        self._rules.clear()
        self._step_summaries.clear()
        self._reapply_filters()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Title
        title_lbl = QLabel("Filter Builder ala Fluxicon Disco")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(
            "Susun rantai tumpukan filter (Filter Stack) secara berjenjang untuk mengeksplorasi\n"
            "dan menyaring kasus berdasarkan atribut, aktivitas awal/akhir, durasi, "
            "urutan, atau waktu."
        )
        desc_lbl.setStyleSheet("font-size: 12.5px; color: #475569;")
        layout.addWidget(desc_lbl)

        # Main Splitter: Left Stack (380px) vs Right Table & KPIs
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #CBD5E1; width: 2px; }")

        # ----------------------------------------------------------------------
        # Left Panel: Filter Stack
        # ----------------------------------------------------------------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(10)

        stack_header = QHBoxLayout()
        stack_title = QLabel("Tumpukan Filter (Filter Stack)")
        stack_title.setStyleSheet("font-size: 13.5px; font-weight: bold; color: #1E293B;")
        stack_header.addWidget(stack_title)
        stack_header.addStretch()

        self.btn_reset_all = QPushButton("Reset Semua")
        self.btn_reset_all.setStyleSheet(
            "background-color: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; "
            "padding: 3px 8px; border-radius: 4px; font-size: 11px;"
        )
        self.btn_reset_all.clicked.connect(self._on_reset_all_clicked)
        stack_header.addWidget(self.btn_reset_all)
        left_layout.addLayout(stack_header)

        self.btn_add_filter = QPushButton("+ Tambah Filter Baru")
        self.btn_add_filter.setStyleSheet(
            "background-color: #2563EB; color: #FFFFFF; font-weight: bold; "
            "padding: 8px 12px; border-radius: 6px; font-size: 13px;"
        )
        self.btn_add_filter.clicked.connect(self._on_add_filter_clicked)
        left_layout.addWidget(self.btn_add_filter)

        # Waterfall Summary Card
        self.waterfall_card = QFrame()
        self.waterfall_card.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #E2E8F0; "
            "border-radius: 6px; padding: 6px;"
        )
        wf_layout = QVBoxLayout(self.waterfall_card)
        wf_layout.setContentsMargins(8, 6, 8, 6)
        wf_layout.setSpacing(2)

        self.lbl_waterfall_title = QLabel("Status Saringan:")
        self.lbl_waterfall_title.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #64748B;"
        )
        wf_layout.addWidget(self.lbl_waterfall_title)

        self.lbl_waterfall_metric = QLabel("Belum ada filter diterapkan.")
        self.lbl_waterfall_metric.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #0F172A;"
        )
        wf_layout.addWidget(self.lbl_waterfall_metric)
        left_layout.addWidget(self.waterfall_card)

        # Scroll area for filter cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
        left_layout.addWidget(self.scroll_area, stretch=1)

        splitter.addWidget(left_widget)

        # ----------------------------------------------------------------------
        # Right Panel: Results, KPIs & Table
        # ----------------------------------------------------------------------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)

        # KPI Cards Row
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)

        self.card_total = self._make_kpi_card("TOTAL KASUS LOLOS", "0 cases", "#2563EB")
        self.card_retention = self._make_kpi_card("RETENSI DATA", "100.00%", "#16A34A")
        self.card_duration = self._make_kpi_card("RATA-RATA DURASI", "0.00 hari", "#D97706")

        kpi_row.addWidget(self.card_total)
        kpi_row.addWidget(self.card_retention)
        kpi_row.addWidget(self.card_duration)
        right_layout.addLayout(kpi_row)

        # Table Toolbar: Search + Drilldown + Export CSV
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        lbl_search = QLabel("Cari Case ID:")
        lbl_search.setStyleSheet("font-weight: bold; color: #1E293B;")
        toolbar.addWidget(lbl_search)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ketik Case ID...")
        self.search_input.setStyleSheet(
            "background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; "
            "border-radius: 4px; padding: 5px 8px;"
        )
        self.search_input.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_input, stretch=1)

        self.btn_drilldown = QPushButton("Lihat di Case Explorer")
        self.btn_drilldown.setStyleSheet(
            "background-color: #2563EB; color: #FFFFFF; font-weight: bold; "
            "padding: 6px 12px; border-radius: 4px; font-size: 12px;"
        )
        self.btn_drilldown.clicked.connect(self._on_drilldown_clicked)
        toolbar.addWidget(self.btn_drilldown)

        self.btn_export = QPushButton("Export Kasus CSV")
        self.btn_export.setStyleSheet(
            "background-color: #F8FAFC; color: #0F172A; border: 1px solid #CBD5E1; "
            "padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 500;"
        )
        self.btn_export.clicked.connect(self._on_export_clicked)
        toolbar.addWidget(self.btn_export)

        right_layout.addLayout(toolbar)

        # Virtualized Table View
        self.table_model = PandasTableModel()
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterKeyColumn(0)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_view.doubleClicked.connect(self._on_table_double_clicked)
        right_layout.addWidget(self.table_view, stretch=1)

        splitter.addWidget(right_widget)
        splitter.setSizes([380, 800])
        layout.addWidget(splitter, stretch=1)

    def _make_kpi_card(self, title: str, init_val: str, val_color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 6px; padding: 10px;"
        )
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748B;")
        c_layout.addWidget(t_lbl)

        v_lbl = QLabel(init_val)
        v_lbl.setObjectName("kpi_value")
        v_lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {val_color};")
        c_layout.addWidget(v_lbl)
        return card

    def _on_search_changed(self, text: str) -> None:
        self.proxy_model.setFilterFixedString(text.strip())

    def _on_add_filter_clicked(self) -> None:
        if self._dataset is None or self._dataset.raw_df.empty:
            QMessageBox.information(
                self, "Belum Ada Dataset", "Silakan impor file log XES terlebih dahulu."
            )
            return

        dialog = AddFilterDialog(self._dataset, self)
        if dialog.exec():
            rule = dialog.get_rule()
            if rule is not None:
                self._rules.append(rule)
                self._reapply_filters()

    def _on_reset_all_clicked(self) -> None:
        if not self._rules:
            return
        reply = QMessageBox.question(
            self,
            "Reset Filter",
            "Apakah Anda yakin ingin menghapus seluruh filter aktif?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._rules.clear()
            self._reapply_filters()

    def _on_rule_toggled(self, idx: int, checked: bool) -> None:
        if 0 <= idx < len(self._rules):
            self._rules[idx].is_enabled = checked
            self._reapply_filters()

    def _on_rule_deleted(self, idx: int) -> None:
        if 0 <= idx < len(self._rules):
            del self._rules[idx]
            self._reapply_filters()

    def _reapply_filters(self) -> None:
        if self._dataset is None:
            self.table_model.set_dataframe(pd.DataFrame())
            self._update_kpis(0, 0, 0.0, 0.0)
            self._render_filter_cards()
            return

        # Execute filter stack
        self._filtered_dataset, self._step_summaries = apply_filter_stack(
            self._dataset, self._rules
        )

        total_orig = self._dataset.overview.total_cases
        total_curr = self._filtered_dataset.overview.total_cases
        total_events_orig = self._dataset.overview.total_events
        total_events_curr = self._filtered_dataset.overview.total_events

        retention_pct = (total_curr / total_orig * 100.0) if total_orig > 0 else 0.0
        mean_dur = self._filtered_dataset.overview.mean_cycle_time_days

        # Update Waterfall text
        if self._rules:
            active_count = sum(1 for r in self._rules if r.is_enabled)
            self.lbl_waterfall_metric.setText(
                f"{total_orig:,} → {total_curr:,} cases ({retention_pct:.2f}%)\n"
                f"{total_events_orig:,} → {total_events_curr:,} events | "
                f"{active_count} filter aktif"
            )
        else:
            self.lbl_waterfall_metric.setText(
                f"Seluruh dataset utuh: {total_orig:,} cases | {total_events_orig:,} events"
            )

        # Update KPIs
        self._update_kpis(total_curr, total_orig, retention_pct, mean_dur)

        # Update Table
        self.table_model.set_dataframe(self._filtered_dataset.case_summary_df)

        # Re-render cards in left panel
        self._render_filter_cards()

    def _update_kpis(
        self, cases: int, total_cases: int, retention_pct: float, mean_duration: float
    ) -> None:
        val_total = self.card_total.findChild(QLabel, "kpi_value")
        if val_total:
            val_total.setText(f"{cases:,} cases")

        val_ret = self.card_retention.findChild(QLabel, "kpi_value")
        if val_ret:
            val_ret.setText(f"{retention_pct:.2f}%")

        val_dur = self.card_duration.findChild(QLabel, "kpi_value")
        if val_dur:
            val_dur.setText(f"{mean_duration:.2f} hari")

    def _render_filter_cards(self) -> None:
        # Clear existing cards layout
        while self.cards_layout.count() > 1:
            child = self.cards_layout.takeAt(0)
            if child is not None:
                w = child.widget()
                if w is not None:
                    w.deleteLater()

        for idx, rule in enumerate(self._rules):
            summary = self._step_summaries[idx] if idx < len(self._step_summaries) else None
            card = FilterCard(idx, rule, summary, self.cards_container)
            card.rule_toggled.connect(self._on_rule_toggled)
            card.rule_deleted.connect(self._on_rule_deleted)
            self.cards_layout.insertWidget(idx, card)

    def _on_drilldown_clicked(self) -> None:
        selected_indexes = self.table_view.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.information(
                self,
                "Pilih Baris Kasus",
                "Silakan pilih salah satu kasus dari tabel terlebih dahulu.",
            )
            return
        row = selected_indexes[0].row()
        source_idx = self.proxy_model.mapToSource(self.proxy_model.index(row, 0))
        case_id = str(self.table_model.data(source_idx, Qt.ItemDataRole.DisplayRole))
        self.request_case_drilldown.emit(case_id, "Disco Filter", None)

    def _on_table_double_clicked(self, index: QModelIndex) -> None:
        source_idx = self.proxy_model.mapToSource(index)
        row = source_idx.row()
        df = self.table_model.get_dataframe()
        if 0 <= row < len(df):
            case_id = str(df.iloc[row]["case_id"])
            self.request_case_drilldown.emit(case_id, "Disco Filter", None)

    def _on_export_clicked(self) -> None:
        if self._filtered_dataset is None or self._filtered_dataset.case_summary_df.empty:
            QMessageBox.information(
                self,
                "Tidak Ada Data",
                "Tidak ada kasus yang dapat diekspor pada hasil filter saat ini.",
            )
            return

        default_name = "filtered_cases.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Ekspor Kasus Hasil Saringan ke CSV",
            default_name,
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        try:
            export_filtered_cases_csv(self._filtered_dataset.case_summary_df, Path(file_path))
            cnt = len(self._filtered_dataset.case_summary_df)
            QMessageBox.information(
                self,
                "Ekspor Berhasil",
                f"Berhasil mengekspor {cnt:,} kasus ke:\n{file_path}",
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Gagal Ekspor", f"Terjadi kesalahan saat mengekspor CSV:\n{exc}"
            )
