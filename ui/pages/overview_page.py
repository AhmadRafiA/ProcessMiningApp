"""Overview page (F01 & F02): dataset metric cards, activity frequency, and case summary table."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRegularExpression, QSortFilterProxyModel, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.models import LoadedDataset
from ui.table_models import PandasTableModel


def _create_metric_card(title: str, value: str, subtext: str = "") -> QFrame:
    """Create a high-contrast KPI metric card widget."""
    card = QFrame()
    card.setStyleSheet(
        """
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 10px;
        }
        """
    )
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(4)

    title_lbl = QLabel(title.upper())
    title_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748B;")
    layout.addWidget(title_lbl)

    val_lbl = QLabel(value)
    val_lbl.setObjectName("metric_value")
    val_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")
    layout.addWidget(val_lbl)

    if subtext:
        sub_lbl = QLabel(subtext)
        sub_lbl.setObjectName("metric_subtext")
        sub_lbl.setStyleSheet("font-size: 11px; color: #475569;")
        layout.addWidget(sub_lbl)

    return card


class OverviewPage(QWidget):
    """Page 1: Event Log Overview and summary statistics."""

    request_case_drilldown = Signal(str, str, object)  # (case_id, exercise_code, highlight_indices)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Header Title
        header_lbl = QLabel("Event Log Overview & Ringkasan Dataset")
        header_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        main_layout.addWidget(header_lbl)

        # 5 Metric Cards in a Grid / Row
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(12)

        self.card_cases = _create_metric_card("Total Cases", "0 cases")
        self.card_events = _create_metric_card("Total Events", "0 events")
        self.card_time = _create_metric_card("Time Range", "-")
        self.card_duration = _create_metric_card("Mean Cycle Time", "0.00 hari")
        self.card_attributes = _create_metric_card("Atribut", "Belum ada dataset")

        self.cards_layout.addWidget(self.card_cases)
        self.cards_layout.addWidget(self.card_events)
        self.cards_layout.addWidget(self.card_time)
        self.cards_layout.addWidget(self.card_duration)
        self.cards_layout.addWidget(self.card_attributes)
        main_layout.addLayout(self.cards_layout)

        # Split View (40% Left: Activity Freq / 60% Right: Case Summary)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(
            """
            QSplitter::handle {
                background-color: #CBD5E1;
                width: 3px;
            }
            """
        )

        # Left Panel: Activity Frequency
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        left_title = QLabel("Distribusi Frekuensi Aktivitas (Terurut Menurun)")
        left_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        left_layout.addWidget(left_title)

        self.activity_table_model = PandasTableModel()
        self.activity_table_view = QTableView()
        self.activity_table_view.setModel(self.activity_table_model)
        self.activity_table_view.setAlternatingRowColors(True)
        self.activity_table_view.horizontalHeader().setStretchLastSection(True)
        left_layout.addWidget(self.activity_table_view)
        splitter.addWidget(left_widget)

        # Right Panel: Case Summary Table with Search Box
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        search_bar_layout = QHBoxLayout()
        search_label = QLabel("Cari Case ID:")
        search_label.setStyleSheet("font-weight: bold; color: #1E293B;")
        search_bar_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ketik Case ID untuk menyaring...")
        self.search_input.setStyleSheet(
            "background-color: #FFFFFF; color: #0F172A; padding: 5px 8px; "
            "border: 1px solid #CBD5E1; border-radius: 4px;"
        )
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_bar_layout.addWidget(self.search_input)
        right_layout.addLayout(search_bar_layout)

        self.case_summary_table_model = PandasTableModel()
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.case_summary_table_model)
        self.proxy_model.setFilterKeyColumn(0)  # Filter by case_id column (column 0)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.case_table_view = QTableView()
        self.case_table_view.setModel(self.proxy_model)
        self.case_table_view.setAlternatingRowColors(True)
        self.case_table_view.horizontalHeader().setStretchLastSection(True)
        self.case_table_view.doubleClicked.connect(self._on_case_double_clicked)
        right_layout.addWidget(self.case_table_view)
        splitter.addWidget(right_widget)

        splitter.setSizes([450, 750])
        main_layout.addWidget(splitter, stretch=1)

    def load_dataset(self, dataset: LoadedDataset) -> None:
        """Populate overview metric cards and tables from loaded dataset."""
        ov = dataset.overview

        # Update card labels
        val_cases = self.card_cases.findChild(QLabel, "metric_value")
        if val_cases:
            val_cases.setText(f"{ov.total_cases:,} cases")

        val_events = self.card_events.findChild(QLabel, "metric_value")
        if val_events:
            val_events.setText(f"{ov.total_events:,} events")

        val_time = self.card_time.findChild(QLabel, "metric_value")
        sub_time = self.card_time.findChild(QLabel, "metric_subtext")
        if val_time:
            val_time.setText(ov.start_time_utc.strftime("%Y-%m-%d"))
        if sub_time:
            sub_time.setText(f"s/d {ov.end_time_utc.strftime('%Y-%m-%d UTC')}")

        val_dur = self.card_duration.findChild(QLabel, "metric_value")
        sub_dur = self.card_duration.findChild(QLabel, "metric_subtext")
        if val_dur:
            val_dur.setText(f"{ov.mean_cycle_time_days:.2f} hari")
        if sub_dur:
            sub_dur.setText(f"Median: {ov.median_cycle_time_days:.2f} hari")

        val_attr = self.card_attributes.findChild(QLabel, "metric_value")
        sub_attr = self.card_attributes.findChild(QLabel, "metric_subtext")
        lifecycle_status = "L: OK" if ov.has_lifecycle else "L: -"
        res_status = "R: OK" if ov.has_resource else "R: -"
        if val_attr:
            val_attr.setText(f"{len(ov.detected_attributes)} Atribut")
        if sub_attr:
            sub_attr.setText(f"Status: {lifecycle_status} | {res_status}")

        # Update tables
        self.activity_table_model.set_dataframe(dataset.activity_freq_df)
        self.case_summary_table_model.set_dataframe(dataset.case_summary_df)

    def clear(self) -> None:
        """Clear all overview tables and reset KPI cards to zero/empty state."""
        self.activity_table_model.set_dataframe(self.activity_table_model._df.iloc[0:0])
        self.case_summary_table_model.set_dataframe(self.case_summary_table_model._df.iloc[0:0])
        self.search_input.clear()

        val_cases = self.card_cases.findChild(QLabel, "metric_value")
        if val_cases:
            val_cases.setText("0 cases")

        val_events = self.card_events.findChild(QLabel, "metric_value")
        if val_events:
            val_events.setText("0 events")

        val_time = self.card_time.findChild(QLabel, "metric_value")
        if val_time:
            val_time.setText("-")

        val_dur = self.card_duration.findChild(QLabel, "metric_value")
        if val_dur:
            val_dur.setText("0.00 hari")

        val_attr = self.card_attributes.findChild(QLabel, "metric_value")
        if val_attr:
            val_attr.setText("Belum ada dataset")

    def _on_search_text_changed(self, text: str) -> None:
        """Filter case table by case_id using regex pattern."""
        pattern = QRegularExpression.escape(text.strip())
        self.proxy_model.setFilterRegularExpression(pattern)

    def _on_case_double_clicked(self, index: Any) -> None:
        """Handle double click on case summary table to drill down into Case Explorer."""
        if not index.isValid():
            return
        src_index = self.proxy_model.mapToSource(index)
        row = src_index.row()
        df = self.case_summary_table_model._df
        if row < 0 or row >= len(df):
            return
        cid = str(df.iloc[row]["case_id"]).strip()
        if cid:
            self.request_case_drilldown.emit(cid, "", None)

