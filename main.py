"""Main entry point for BPIC17 Event Log Analyzer desktop application."""

import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.theme import apply_light_theme


def main() -> None:
    """Launch BPIC17 Event Log Analyzer PySide6 application."""
    app = QApplication(sys.argv)
    app.setApplicationName("BPIC17 Event Log Analyzer")
    app.setOrganizationName("Datmin")

    # Enforce High-Contrast Light Theme (overrides OS dark mode for tables & inputs)
    apply_light_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
