"""
Main Window for Toolkit GUI.
Orchestrates the navigation sidebar, modular tool deck views,
live terminal console drawer, and global keyboard shortcuts.
"""

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.gui.components.console_drawer import ConsoleDrawer
from ui.gui.components.sidebar import Sidebar
from ui.gui.components.toast import ToastNotification
from ui.gui.theme import CYBER_THEME_QSS
from ui.gui.views.downloader_view import DownloaderView
from ui.gui.views.email_view import EmailView
from ui.gui.views.password_view import PasswordView
from ui.gui.views.phone_view import PhoneView
from ui.gui.views.qr_view import QRView
from ui.gui.views.sysinfo_view import SysInfoView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Toolkit — Cyber Control Center")
        self.resize(1180, 760)
        self.setMinimumSize(640, 460)

        # App Icon
        base_dir = getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent.parent)
        icon_path = Path(base_dir) / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._init_ui()
        self._init_shortcuts()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Navigation Sidebar
        self.sidebar = Sidebar()
        self.sidebar.tab_selected.connect(self._on_tab_changed)
        root_layout.addWidget(self.sidebar)

        # 2. Right Deck Container
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Stacked Views Deck
        self.deck = QStackedWidget()

        self.downloader_view = DownloaderView()
        self.password_view = PasswordView()
        self.phone_view = PhoneView()
        self.qr_view = QRView()
        self.email_view = EmailView()
        self.sysinfo_view = SysInfoView()

        self.views = [
            self.downloader_view,
            self.password_view,
            self.phone_view,
            self.qr_view,
            self.email_view,
            self.sysinfo_view,
        ]

        for view in self.views:
            self.deck.addWidget(view)
            # Wire logs & toasts
            view.log_requested.connect(self._log)
            view.toast_requested.connect(self._toast)

        right_layout.addWidget(self.deck, 1)

        # Bottom Live Console Drawer
        self.console_drawer = ConsoleDrawer()
        right_layout.addWidget(self.console_drawer)

        root_layout.addWidget(right_container, 1)

        # Floating Toast Notification
        self.toast = ToastNotification(self)

        self._log("⚡ Toolkit Cyber Matrix initialized and ready.")

    def _init_shortcuts(self):
        # Ctrl+L toggle console
        shortcut_console = QShortcut(QKeySequence("Ctrl+L"), self)
        shortcut_console.activated.connect(self.console_drawer.toggle_drawer)

        # Ctrl+B toggle sidebar
        shortcut_sidebar = QShortcut(QKeySequence("Ctrl+B"), self)
        shortcut_sidebar.activated.connect(self.sidebar.toggle_collapse)

        # Ctrl+1 to 6 tabs
        for idx in range(6):
            seq = f"Ctrl+{idx + 1}"
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(lambda i=idx: self.sidebar.select_tab(i))

        # Ctrl+Q quit
        shortcut_quit = QShortcut(QKeySequence("Ctrl+Q"), self)
        shortcut_quit.activated.connect(self.close)

    def _on_tab_changed(self, index: int):
        if 0 <= index < self.deck.count():
            self.deck.setCurrentIndex(index)
            view_name = self.sidebar.NAV_ITEMS[index]["title"]
            self.console_drawer.set_status(f"ACTIVE: {view_name.upper()}", True)

    def _log(self, text: str):
        self.console_drawer.append_log(text)

    def _toast(self, message: str, is_error: bool = False):
        icon = "✗" if is_error else "✓"
        self.toast.show_message(message, icon=icon, is_error=is_error)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Responsive automatic sidebar collapse/expand on window resize
        if self.width() < 860 and not self.sidebar.is_collapsed:
            self.sidebar.set_collapsed(True)
        elif self.width() >= 860 and self.sidebar.is_collapsed:
            self.sidebar.set_collapsed(False)

        # Keep toast centered at bottom
        if self.toast.isVisible():
            x = (self.width() - self.toast.width()) // 2
            y = self.height() - self.toast.height() - 48
            self.toast.move(x, y)
