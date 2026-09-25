"""
Toolkit GUI Entry Point.
"""

import sys
from PyQt6.QtWidgets import QApplication
from ui.gui.main_window import MainWindow
from ui.gui.theme import CYBER_THEME_QSS


def run_gui() -> int:
    """Launch the Toolkit PyQt6 GUI application."""
    app = QApplication(sys.argv)
    app.setStyleSheet(CYBER_THEME_QSS)

    window = MainWindow()
    window.show()

    return app.exec()


__all__ = ["run_gui", "MainWindow"]
