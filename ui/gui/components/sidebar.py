"""
Sidebar navigation component for Toolkit GUI.
Provides quick switching between tools with Cyberpunk matrix styling,
collapsible compact mode for small window widths, and keyboard shortcuts.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.gui.theme import (
    ACCENT_CYAN,
    ACCENT_EMERALD,
    BORDER_SUBTLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class Sidebar(QFrame):
    tab_selected = pyqtSignal(int)
    collapse_toggled = pyqtSignal(bool)

    NAV_ITEMS = [
        {"icon": "📥", "title": "Media Downloader", "shortcut": "1"},
        {"icon": "🔐", "title": "Password Vault", "shortcut": "2"},
        {"icon": "📱", "title": "Phone Checker", "shortcut": "3"},
        {"icon": "🏁", "title": "QR Code Studio", "shortcut": "4"},
        {"icon": "📨", "title": "Message Sender", "shortcut": "5"},
        {"icon": "📊", "title": "System Telemetry", "shortcut": "6"},
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(230)
        self.buttons: list[QPushButton] = []
        self.current_index = 0
        self.is_collapsed = False

        self._init_ui()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 16, 12, 16)
        self.layout.setSpacing(8)

        # Header / Brand
        self.header_widget = QWidget()
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(4, 0, 4, 0)
        header_layout.setSpacing(6)

        brand_box = QVBoxLayout()
        brand_box.setSpacing(2)

        self.logo = QLabel("⚡ TOOLKIT")
        self.logo.setObjectName("SidebarLogo")
        brand_box.addWidget(self.logo)

        self.sub = QLabel("CYBER CONTROL")
        self.sub.setObjectName("SidebarSub")
        brand_box.addWidget(self.sub)

        header_layout.addLayout(brand_box)
        header_layout.addStretch()

        # Collapse / Expand toggle button
        self.toggle_collapse_btn = QPushButton("◀")
        self.toggle_collapse_btn.setProperty("class", "SecondaryBtn")
        self.toggle_collapse_btn.setFixedSize(26, 26)
        self.toggle_collapse_btn.setToolTip("Toggle Compact Sidebar (Ctrl+B)")
        self.toggle_collapse_btn.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.toggle_collapse_btn)

        self.layout.addWidget(self.header_widget)
        self.layout.addSpacing(10)

        # Nav items
        self.nav_label = QLabel("MODULES")
        self.nav_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-weight: 800; letter-spacing: 1.5px; padding-left: 6px;"
        )
        self.layout.addWidget(self.nav_label)

        for i, item in enumerate(self.NAV_ITEMS):
            btn = QPushButton(f"{item['icon']}   {item['title']}")
            btn.setProperty("class", "NavBtn")
            btn.setToolTip(f"{item['title']} (Ctrl+{item['shortcut']})")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self.select_tab(idx))
            self.buttons.append(btn)
            self.layout.addWidget(btn)

        self.layout.addStretch()

        # Footer version badge
        self.footer_frame = QFrame()
        self.footer_frame.setStyleSheet(
            f"background: rgba(0, 255, 157, 0.04); border: 1px solid rgba(0, 255, 157, 0.15); border-radius: 8px; padding: 6px;"
        )
        footer_layout = QVBoxLayout(self.footer_frame)
        footer_layout.setContentsMargins(6, 6, 6, 6)
        footer_layout.setSpacing(2)

        self.status_line = QLabel("● ONLINE")
        self.status_line.setStyleSheet(
            f"color: {ACCENT_EMERALD}; font-weight: 800; font-size: 10px; letter-spacing: 1px;"
        )
        self.version_line = QLabel("v1.0.0")
        self.version_line.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 9px;")

        footer_layout.addWidget(self.status_line)
        footer_layout.addWidget(self.version_line)
        self.layout.addWidget(self.footer_frame)

        self.select_tab(0)

    def select_tab(self, index: int):
        if 0 <= index < len(self.buttons):
            self.current_index = index
            for i, btn in enumerate(self.buttons):
                is_active = i == index
                btn.setProperty("active", "true" if is_active else "false")
                btn.style().unpolish(btn)
                btn.style().polish(btn)

            self.tab_selected.emit(index)

    def toggle_collapse(self):
        self.set_collapsed(not self.is_collapsed)

    def set_collapsed(self, collapse: bool):
        self.is_collapsed = collapse
        if self.is_collapsed:
            self.setFixedWidth(64)
            self.logo.setText("⚡")
            self.sub.hide()
            self.nav_label.hide()
            self.footer_frame.hide()
            self.toggle_collapse_btn.setText("▶")
            for i, btn in enumerate(self.buttons):
                btn.setText(self.NAV_ITEMS[i]["icon"])
                btn.setStyleSheet("text-align: center; padding: 10px 0px;")
        else:
            self.setFixedWidth(230)
            self.logo.setText("⚡ TOOLKIT")
            self.sub.show()
            self.nav_label.show()
            self.footer_frame.show()
            self.toggle_collapse_btn.setText("◀")
            for i, btn in enumerate(self.buttons):
                btn.setText(f"{self.NAV_ITEMS[i]['icon']}   {self.NAV_ITEMS[i]['title']}")
                btn.setStyleSheet("")

        self.collapse_toggled.emit(self.is_collapsed)
