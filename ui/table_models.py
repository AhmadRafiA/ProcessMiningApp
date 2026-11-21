"""Virtualized table model (QAbstractTableModel) for efficient Pandas DataFrame rendering."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtGui import QColor, QFont

EVIDENCE_BG_COLOR = QColor("#FEF08A")  # Soft yellow
EVIDENCE_TEXT_COLOR = QColor("#713F12")  # Deep amber/brown
DEFAULT_CELL_TEXT_COLOR = QColor("#0F172A")  # High contrast slate 900
DEFAULT_HEADER_TEXT_COLOR = QColor("#1E293B")  # Deep slate 800

COLUMN_HEADER_LABELS: dict[str, str] = {
    "_orig_idx": "XES Row Index",
    "case:concept:name": "Case ID",
    "concept:name": "Activity",
    "time:timestamp": "Timestamp (UTC)",
    "lifecycle:transition": "Lifecycle",
    "org:resource": "Resource",
    "case_id": "Case ID",
    "event_count": "Events",
    "start_time": "Start Time (UTC)",
    "end_time": "End Time (UTC)",
    "cycle_time_days": "Cycle Time",
    "first_activity": "First Activity",
    "last_activity": "Last Activity",
    "activity_name": "Activity Name",
    "case_count": "Case Count",
    "case_coverage_pct": "Coverage (%)",
    "matching_event_count": "Matching Events",
    "complete_count": "Complete Count",
    "matching_resources": "Matching Resources",
    "max_resource_complete_count": "Max Complete by Resource",
    "total_fraud_complete_count": "Total Complete",
    "first_cancelled_idx": "Cancelled Event Index",
    "first_cancelled_time": "Cancelled Time (UTC)",
    "following_accepted_idx": "Accepted Event Index",
    "following_accepted_time": "Accepted Time (UTC)",
    "step_no": "Step #",
    "is_evidence": "Evidence?",
    "evidence_badge": "Badge",
}


# Module-level default index to satisfy B008
_DEFAULT_INDEX = QModelIndex()


class PandasTableModel(QAbstractTableModel):
    """Memory-efficient, virtualized table model for PySide6 QTableView."""

    def __init__(
        self,
        df: pd.DataFrame | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._df: pd.DataFrame = df.copy() if df is not None else pd.DataFrame()
        self._bold_font = QFont()
        self._bold_font.setBold(True)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        """Replace active DataFrame and trigger a full view reset."""
        self.beginResetModel()
        self._df = df.copy()
        self.endResetModel()

    def get_dataframe(self) -> pd.DataFrame:
        """Return a copy of the current DataFrame."""
        return self._df.copy()

    def rowCount(  # noqa: N802
        self, parent: QModelIndex | QPersistentModelIndex = _DEFAULT_INDEX
    ) -> int:
        if parent.isValid() or self._df.empty:
            return 0
        return int(len(self._df))

    def columnCount(  # noqa: N802
        self, parent: QModelIndex | QPersistentModelIndex = _DEFAULT_INDEX
    ) -> int:
        if parent.isValid() or self._df.empty:
            return 0
        return int(len(self._df.columns))

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid() or self._df.empty:
            return None

        row = index.row()
        col = index.column()
        if row < 0 or row >= len(self._df) or col < 0 or col >= len(self._df.columns):
            return None

        col_name = str(self._df.columns[col])
        val = self._df.iat[row, col]

        # Check if current row represents evidence
        is_evidence_row = False
        if "is_evidence" in self._df.columns:
            is_evidence_row = bool(self._df.at[self._df.index[row], "is_evidence"])

        if role == Qt.ItemDataRole.DisplayRole:
            return self._format_display_value(col_name, val)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return self._get_alignment(col_name, val)

        if role == Qt.ItemDataRole.BackgroundRole and is_evidence_row:
            return EVIDENCE_BG_COLOR

        if role == Qt.ItemDataRole.ForegroundRole:
            if is_evidence_row:
                return EVIDENCE_TEXT_COLOR
            return DEFAULT_CELL_TEXT_COLOR

        if role == Qt.ItemDataRole.FontRole and is_evidence_row:
            return self._bold_font

        return None

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.ForegroundRole:
            return DEFAULT_HEADER_TEXT_COLOR

        if role == Qt.ItemDataRole.FontRole and orientation == Qt.Orientation.Horizontal:
            return self._bold_font

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            if not self._df.empty and 0 <= section < len(self._df.columns):
                raw_name = str(self._df.columns[section])
                return COLUMN_HEADER_LABELS.get(raw_name, raw_name)
            return None

        if orientation == Qt.Orientation.Vertical:
            return str(section + 1)

        return None

    def _format_display_value(self, col_name: str, val: Any) -> str:
        """Format cell value according to data types and business rules."""
        if pd.isna(val) or val is None:
            return "-"

        # Duration formatting: 2 decimals + ' hari'
        if "cycle_time" in col_name and isinstance(val, (int, float, np.floating)):
            return f"{float(val):.2f} hari"

        # Percentage formatting: 2 decimals + '%'
        if (
            "pct" in col_name or "percentage" in col_name or "coverage" in col_name
        ) and isinstance(val, (int, float, np.floating)):
            return f"{float(val):.2f}%"

        # Integer counts with thousands separator
        if (
            isinstance(val, (int, np.integer))
            and ("count" in col_name or col_name in {"total_cases", "total_events"})
        ):
            return f"{int(val):,}"

        # ISO UTC timestamps
        if isinstance(val, pd.Timestamp):
            return str(val.strftime("%Y-%m-%d %H:%M:%S UTC"))

        return str(val)

    def _get_alignment(self, col_name: str, val: Any) -> Qt.AlignmentFlag:
        """Determine horizontal and vertical alignment for a cell."""
        if isinstance(val, (int, float, np.number)) and not isinstance(val, bool):
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        if col_name in {
            "case_id",
            "case:concept:name",
            "_orig_idx",
            "step_no",
            "lifecycle:transition",
            "is_evidence",
            "evidence_badge",
        }:
            return Qt.AlignmentFlag.AlignCenter

        return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
