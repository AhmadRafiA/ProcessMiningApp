"""Theme and styling configuration for BPIC17 Event Log Analyzer.

Enforces a high-contrast light theme across all platforms (macOS, Windows, Linux)
regardless of the host operating system's dark/light mode setting.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

# Canonical Design System Colors (DESIGN_SYSTEM.md Section 3)
COLOR_BG_APP = "#F8FAFC"          # Slate 50 - Main window background
COLOR_BG_CARD = "#FFFFFF"         # Pure white - Cards & tables
COLOR_BG_HEADER = "#F1F5F9"       # Slate 100 - Table header background
COLOR_BG_ROW_ALT = "#F8FAFC"      # Slate 50 - Alternating row background

COLOR_TEXT_PRIMARY = "#0F172A"    # Slate 900 - High contrast text
COLOR_TEXT_SECONDARY = "#334155"  # Slate 700 - Sub-labels
COLOR_TEXT_MUTED = "#64748B"      # Slate 500 - Captions & metadata
COLOR_TEXT_HEADER = "#1E293B"     # Slate 800 - Table header text

COLOR_BORDER_SUBTLE = "#E2E8F0"   # Slate 200 - Gridlines & card borders
COLOR_BORDER_STRONG = "#CBD5E1"   # Slate 300 - Input borders & active dividers

COLOR_PRIMARY = "#2563EB"         # Blue 600 - Primary actions & selections
COLOR_PRIMARY_HOVER = "#1D4ED8"   # Blue 700 - Button hover state
COLOR_PRIMARY_TEXT = "#FFFFFF"    # Selected row text & primary button text

COLOR_SUCCESS_BG = "#DCFCE7"      # Green 100
COLOR_SUCCESS_TEXT = "#15803D"    # Green 700

COLOR_WARNING_BG = "#FEF3C7"      # Amber 100
COLOR_WARNING_TEXT = "#B45309"    # Amber 700

COLOR_DANGER_BG = "#FEE2E2"       # Red 100
COLOR_DANGER_TEXT = "#B91C1C"     # Red 700


GLOBAL_STYLESHEET = f"""
/* Global Reset & Base Typography */
QWidget {{
    color: {COLOR_TEXT_PRIMARY};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    font-size: 13px;
}}

QMainWindow, QStackedWidget {{
    background-color: {COLOR_BG_APP};
}}

/* High-Contrast Virtualized Tables (QTableView) */
QTableView {{
    background-color: {COLOR_BG_CARD};
    alternate-background-color: {COLOR_BG_ROW_ALT};
    color: {COLOR_TEXT_PRIMARY};
    gridline-color: {COLOR_BORDER_SUBTLE};
    selection-background-color: {COLOR_PRIMARY};
    selection-color: {COLOR_PRIMARY_TEXT};
    border: 1px solid {COLOR_BORDER_STRONG};
    border-radius: 6px;
    font-size: 12.5px;
}}

QTableView::item {{
    color: {COLOR_TEXT_PRIMARY};
    padding: 4px 6px;
    border: none;
}}

QTableView::item:selected {{
    background-color: {COLOR_PRIMARY};
    color: {COLOR_PRIMARY_TEXT};
}}

/* Table Headers */
QHeaderView::section {{
    background-color: {COLOR_BG_HEADER};
    color: {COLOR_TEXT_HEADER};
    font-weight: bold;
    font-size: 12px;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid {COLOR_BORDER_SUBTLE};
    border-bottom: 1px solid {COLOR_BORDER_STRONG};
}}

QHeaderView::section:vertical {{
    background-color: {COLOR_BG_ROW_ALT};
    color: {COLOR_TEXT_MUTED};
    font-weight: normal;
    font-size: 11px;
    padding: 4px 6px;
    border: none;
    border-right: 1px solid {COLOR_BORDER_STRONG};
    border-bottom: 1px solid {COLOR_BORDER_SUBTLE};
}}

/* Search Inputs & Text Fields */
QLineEdit {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER_STRONG};
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 13px;
    selection-background-color: {COLOR_PRIMARY};
    selection-color: {COLOR_PRIMARY_TEXT};
}}

QLineEdit:focus {{
    border: 1px solid {COLOR_PRIMARY};
}}

QTextEdit {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER_SUBTLE};
    border-radius: 6px;
    padding: 8px;
    selection-background-color: {COLOR_PRIMARY};
    selection-color: {COLOR_PRIMARY_TEXT};
}}

/* Slim Modern Scrollbars */
QScrollBar:vertical {{
    background: {COLOR_BG_APP};
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: {COLOR_BORDER_STRONG};
    min-height: 24px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_TEXT_MUTED};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: {COLOR_BG_APP};
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background: {COLOR_BORDER_STRONG};
    min-width: 24px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLOR_TEXT_MUTED};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Tooltips */
QToolTip {{
    background-color: #0F172A;
    color: #FFFFFF;
    border: 1px solid #334155;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}}
"""


def create_light_palette() -> QPalette:
    """Build a complete, explicit light palette to override OS dark-mode defaults."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLOR_BG_APP))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLOR_TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(COLOR_BG_CARD))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(COLOR_BG_ROW_ALT))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#0F172A"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Text, QColor(COLOR_TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(COLOR_BG_HEADER))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLOR_TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(COLOR_DANGER_TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLOR_PRIMARY))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(COLOR_PRIMARY_TEXT))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(COLOR_TEXT_MUTED))
    return palette


def apply_light_theme(target: QApplication | QWidget | None = None) -> None:
    """Apply the high-contrast light palette and stylesheet to the target or active app."""
    palette = create_light_palette()

    if target is None:
        app = QApplication.instance()
        if app is not None and isinstance(app, QApplication):
            app.setPalette(palette)
            app.setStyleSheet(GLOBAL_STYLESHEET)
        return

    if isinstance(target, QApplication):
        target.setPalette(palette)
        target.setStyleSheet(GLOBAL_STYLESHEET)
    elif isinstance(target, QWidget):
        target.setPalette(palette)
        # Apply stylesheet to parent app if available, else widget
        app = QApplication.instance()
        if app is not None and isinstance(app, QApplication):
            app.setStyleSheet(GLOBAL_STYLESHEET)
            app.setPalette(palette)
        else:
            target.setStyleSheet(GLOBAL_STYLESHEET)
