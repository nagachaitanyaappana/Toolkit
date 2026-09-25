"""
Live ANSI / Terminal Console Drawer component.
Displays non-blocking execution logs with timestamps and matrix styling.
"""

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.gui.theme import (
    ACCENT_CYAN,
    ACCENT_EMERALD,
    BG_CARD,
    BG_DRAWER,
    BORDER_SUBTLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
)


class ConsoleDrawer(QFrame):
    toggled = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ConsoleDrawer")
        self.is_collapsed = True
        self.autoscroll = True

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 12)
        layout.setSpacing(6)

        # Header bar
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self.title_label = QLabel("📟 LIVE SYSTEM CONSOLE")
        self.title_label.setStyleSheet(
            f"color: {ACCENT_CYAN}; font-weight: 800; font-size: 11px; letter-spacing: 1px;"
        )
        header_layout.addWidget(self.title_label)

        self.status_label = QLabel("IDLE")
        self.status_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-weight: 700; background: rgba(255,255,255,0.05); padding: 2px 8px; border-radius: 4px;"
        )
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        self.auto_scroll_cb.stateChanged.connect(self._toggle_autoscroll)
        header_layout.addWidget(self.auto_scroll_cb)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setProperty("class", "SecondaryBtn")
        self.copy_btn.setFixedHeight(26)
        self.copy_btn.setStyleSheet(f"font-size: 11px; padding: 2px 10px; border-radius: 4px;")
        self.copy_btn.clicked.connect(self._copy_logs)
        header_layout.addWidget(self.copy_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setProperty("class", "SecondaryBtn")
        self.clear_btn.setFixedHeight(26)
        self.clear_btn.setStyleSheet(f"font-size: 11px; padding: 2px 10px; border-radius: 4px;")
        self.clear_btn.clicked.connect(self.clear_logs)
        header_layout.addWidget(self.clear_btn)

        self.toggle_btn = QPushButton("▲ Open (Ctrl+L)")
        self.toggle_btn.setProperty("class", "SecondaryBtn")
        self.toggle_btn.setFixedHeight(26)
        self.toggle_btn.setStyleSheet(f"font-size: 11px; padding: 2px 10px; border-radius: 4px; color: {ACCENT_EMERALD};")
        self.toggle_btn.clicked.connect(self.toggle_drawer)
        header_layout.addWidget(self.toggle_btn)

        layout.addWidget(header)

        # Log content view
        self.text_area = QPlainTextEdit()
        self.text_area.setObjectName("ConsoleOutput")
        self.text_area.setReadOnly(True)
        self.text_area.setMaximumBlockCount(2000)
        self.text_area.hide()
        layout.addWidget(self.text_area)

        self.setFixedHeight(44)

    def append_log(self, text: str, level: str = "info"):
        now = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{now}]"
        
        clean_text = text.rstrip("\r\n")
        if not clean_text:
            return

        # If there are carriage returns, handle inline progress updates
        lines = clean_text.splitlines()
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            self.text_area.appendPlainText(f"{prefix} {line_str}")

        if self.autoscroll:
            self.text_area.moveCursor(QTextCursor.MoveOperation.End)

    def set_status(self, text: str, is_active: bool = False):
        self.status_label.setText(text.upper())
        if is_active:
            self.status_label.setStyleSheet(
                f"color: {ACCENT_EMERALD}; font-size: 10px; font-weight: 700; background: rgba(0,255,157,0.15); border: 1px solid {ACCENT_EMERALD}; padding: 2px 8px; border-radius: 4px;"
            )
        else:
            self.status_label.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 10px; font-weight: 700; background: rgba(255,255,255,0.05); padding: 2px 8px; border-radius: 4px;"
            )

    def clear_logs(self):
        self.text_area.clear()

    def _copy_logs(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.text_area.toPlainText())

    def _toggle_autoscroll(self, state: int):
        self.autoscroll = (state == Qt.CheckState.Checked.value or state == 2)

    def toggle_drawer(self):
        if self.is_collapsed:
            self.expand_drawer()
        else:
            self.collapse_drawer()

    def expand_drawer(self):
        self.is_collapsed = False
        self.text_area.show()
        self.setFixedHeight(220)
        self.toggle_btn.setText("▼ Hide (Ctrl+L)")
        self.toggled.emit(True)

    def collapse_drawer(self):
        self.is_collapsed = True
        self.text_area.hide()
        self.setFixedHeight(44)
        self.toggle_btn.setText("▲ Open (Ctrl+L)")
        self.toggled.emit(False)
