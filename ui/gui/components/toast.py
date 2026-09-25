"""
Toast notification widget for quick feedback (e.g. copied to clipboard, success).
"""

from PyQt6.QtCore import QPoint, QPropertyAnimation, Qt, QTimer
from PyQt6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

from ui.gui.theme import ACCENT_EMERALD, ACCENT_ERROR, BG_CARD, TEXT_PRIMARY


class ToastNotification(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {ACCENT_EMERALD};
                border-radius: 8px;
                padding: 4px 14px;
            }}
            QLabel {{
                color: {TEXT_PRIMARY};
                font-weight: 700;
                font-size: 12px;
                background: transparent;
            }}
        """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        self.icon_label = QLabel("⚡")
        self.icon_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.icon_label)

        self.text_label = QLabel("")
        layout.addWidget(self.text_label)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.hide()

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_message(self, message: str, icon: str = "✓", is_error: bool = False, duration_ms: int = 2500):
        self.icon_label.setText(icon)
        self.text_label.setText(message)

        border_color = ACCENT_ERROR if is_error else ACCENT_EMERALD
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 4px 14px;
            }}
            QLabel {{
                color: {TEXT_PRIMARY};
                font-weight: 700;
                font-size: 12px;
                background: transparent;
            }}
        """
        )

        self.adjustSize()
        if self.parentWidget():
            parent_rect = self.parentWidget().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = parent_rect.height() - self.height() - 48
            self.move(x, y)

        self.show()
        self.raise_()
        self._hide_timer.start(duration_ms)
