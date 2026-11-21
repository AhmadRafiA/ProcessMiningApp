"""Unit tests for UI high-contrast light theme and palette configuration."""

from __future__ import annotations

import os

import pytest
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from ui.main_window import MainWindow
from ui.theme import (
    COLOR_BG_CARD,
    COLOR_PRIMARY,
    COLOR_PRIMARY_TEXT,
    COLOR_TEXT_PRIMARY,
    apply_light_theme,
    create_light_palette,
)


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Headless QApplication fixture."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    assert isinstance(app, QApplication)
    return app


def test_create_light_palette(qapp: QApplication) -> None:
    """Test that light palette explicitly enforces dark text on light backgrounds."""
    palette = create_light_palette()

    # High-contrast text colors
    assert palette.color(QPalette.ColorRole.Text).name().lower() == COLOR_TEXT_PRIMARY.lower()
    assert palette.color(QPalette.ColorRole.WindowText).name().lower() == COLOR_TEXT_PRIMARY.lower()
    assert palette.color(QPalette.ColorRole.ButtonText).name().lower() == COLOR_TEXT_PRIMARY.lower()

    # Light background colors
    assert palette.color(QPalette.ColorRole.Base).name().lower() == COLOR_BG_CARD.lower()

    # Selection colors
    assert palette.color(QPalette.ColorRole.Highlight).name().lower() == COLOR_PRIMARY.lower()
    assert (
        palette.color(QPalette.ColorRole.HighlightedText).name().lower()
        == COLOR_PRIMARY_TEXT.lower()
    )

    # Text must NOT equal background
    assert palette.color(QPalette.ColorRole.Text) != palette.color(QPalette.ColorRole.Base)


def test_apply_light_theme_to_main_window(qapp: QApplication) -> None:
    """Test that MainWindow has light palette and readable text colors applied."""
    win = MainWindow()
    apply_light_theme(win)

    table_overview = win.page_overview.activity_table_view
    pal = table_overview.palette()

    # Verify text is dark and distinct from base background
    text_color = pal.color(QPalette.ColorRole.Text)
    base_color = pal.color(QPalette.ColorRole.Base)
    assert text_color != base_color
    assert text_color.name().lower() == COLOR_TEXT_PRIMARY.lower()

    # Verify Case Explorer table has dark text
    table_explorer = win.page_case_explorer.table_view
    exp_pal = table_explorer.palette()
    assert exp_pal.color(QPalette.ColorRole.Text).name().lower() == COLOR_TEXT_PRIMARY.lower()

    win.close()
    qapp.processEvents()
