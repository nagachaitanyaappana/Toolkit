"""
Cyberpunk Emerald Matrix Theme for Toolkit GUI.
Features a seamless, unified dark obsidian canvas, glowing emerald accents (#00ff9d),
clean transparent labels/rows, and eliminated harsh background striping.
"""

from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget

# Unified Palette Constants
BG_BASE = "#0b0f14"
BG_SIDEBAR = "#0e131a"
BG_CARD = "#121822"
BG_SURFACE = "#0f151e"
BG_INPUT = "#151e2a"
BG_DRAWER = "#090d12"

BORDER_SUBTLE = "#1e2938"
BORDER_FOCUS = "#00ff9d"
BORDER_CYAN = "#00e5ff"

ACCENT_EMERALD = "#00ff9d"
ACCENT_CYAN = "#00e5ff"
ACCENT_PURPLE = "#a855f7"
ACCENT_WARN = "#f59e0b"
ACCENT_ERROR = "#ef4444"

TEXT_PRIMARY = "#f8fafc"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED = "#64748b"

CYBER_THEME_QSS = f"""
/* ─── Global Window ─── */
QMainWindow {{
    background-color: {BG_BASE};
}}

QWidget {{
    color: {TEXT_PRIMARY};
    font-family: "Inter", "Segoe UI", -apple-system, Roboto, Ubuntu, sans-serif;
    font-size: 13px;
    outline: none;
}}

/* Ensure all labels, checkboxes, and layout rows don't paint clashing backgrounds */
QLabel {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
}}

QCheckBox {{
    background-color: transparent;
    spacing: 8px;
    color: {TEXT_PRIMARY};
}}

QRadioButton {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
}}

QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* ─── Sidebar Navigation ─── */
QFrame#Sidebar {{
    background-color: {BG_SIDEBAR};
    border-right: 1px solid {BORDER_SUBTLE};
}}

QLabel#SidebarLogo {{
    color: {ACCENT_EMERALD};
    font-size: 18px;
    font-weight: 900;
    letter-spacing: 1.5px;
}}

QLabel#SidebarSub {{
    color: {TEXT_MUTED};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
}}

QPushButton.NavBtn {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    text-align: left;
    padding: 12px 16px;
    border-radius: 8px;
    border: 1px solid transparent;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton.NavBtn:hover {{
    background-color: rgba(0, 255, 157, 0.08);
    color: {ACCENT_EMERALD};
    border: 1px solid rgba(0, 255, 157, 0.25);
}}

QPushButton.NavBtn[active="true"] {{
    background-color: rgba(0, 255, 157, 0.14);
    color: {ACCENT_EMERALD};
    font-weight: 700;
    border: 1px solid {ACCENT_EMERALD};
}}

/* ─── Unified Clean Cards ─── */
QFrame.CyberCard {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 12px;
    padding: 16px;
}}

QFrame.CyberCard:hover {{
    border: 1px solid rgba(0, 255, 157, 0.35);
}}

/* ─── Typography Headers ─── */
QLabel.ViewTitle {{
    color: {TEXT_PRIMARY};
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 0.5px;
}}

QLabel.ViewSubtitle {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

QLabel.CardTitle {{
    color: {ACCENT_CYAN};
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

QLabel.MetricValue {{
    color: {ACCENT_EMERALD};
    font-size: 28px;
    font-weight: 900;
    letter-spacing: -0.5px;
}}

QLabel.MetricLabel {{
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}

/* ─── Input Elements ─── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 8px;
    padding: 8px 12px;
    selection-background-color: rgba(0, 255, 157, 0.3);
    selection-color: #ffffff;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {BORDER_FOCUS};
    background-color: #182332;
}}

QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover {{
    border: 1px solid rgba(0, 255, 157, 0.4);
}}

/* ─── Buttons ─── */
QPushButton.PrimaryBtn {{
    background-color: {ACCENT_EMERALD};
    color: #041009;
    border: none;
    border-radius: 8px;
    font-weight: 800;
    font-size: 13px;
    padding: 10px 18px;
}}

QPushButton.PrimaryBtn:hover {{
    background-color: #1affad;
}}

QPushButton.PrimaryBtn:pressed {{
    background-color: #00cc7d;
}}

QPushButton.PrimaryBtn:disabled {{
    background-color: #182721;
    color: #3f554c;
}}

QPushButton.SecondaryBtn {{
    background-color: rgba(255, 255, 255, 0.04);
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 8px;
    font-weight: 600;
    padding: 8px 14px;
}}

QPushButton.SecondaryBtn:hover {{
    background-color: rgba(0, 229, 255, 0.08);
    border: 1px solid {BORDER_CYAN};
    color: {ACCENT_CYAN};
}}

QPushButton.SecondaryBtn:pressed {{
    background-color: rgba(0, 229, 255, 0.16);
}}

QPushButton.DangerBtn {{
    background-color: rgba(239, 68, 68, 0.12);
    color: {ACCENT_ERROR};
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 8px;
    font-weight: 600;
    padding: 8px 14px;
}}

QPushButton.DangerBtn:hover {{
    background-color: rgba(239, 68, 68, 0.25);
    border: 1px solid {ACCENT_ERROR};
}}

/* ─── Progress Bar ─── */
QProgressBar {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    height: 14px;
    text-align: center;
    font-size: 10px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #00c675, stop:1 {ACCENT_EMERALD});
    border-radius: 5px;
}}

/* ─── Tables ─── */
QTableWidget {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 8px;
    gridline-color: transparent;
    color: {TEXT_PRIMARY};
}}

QTableWidget::item {{
    padding: 8px;
    background-color: transparent;
}}

QTableWidget::item:selected {{
    background-color: rgba(0, 255, 157, 0.12);
    color: {ACCENT_EMERALD};
}}

QHeaderView::section {{
    background-color: {BG_SIDEBAR};
    color: {TEXT_SECONDARY};
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.5px;
    padding: 8px;
    border: none;
    border-bottom: 1px solid {BORDER_SUBTLE};
}}

/* ─── Scrollbars ─── */
QScrollBar:vertical {{
    background: {BG_BASE};
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: #1c2736;
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {ACCENT_EMERALD};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: {BG_BASE};
    height: 8px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: #1c2736;
    min-width: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {ACCENT_EMERALD};
}}

/* ─── Dropdown / ComboBox ─── */
QComboBox {{
    background-color: {BG_INPUT};
    padding: 6px 12px;
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_SUBTLE};
    selection-background-color: rgba(0, 255, 157, 0.15);
    selection-color: {ACCENT_EMERALD};
    padding: 4px;
}}

/* ─── CheckBox Indicator ─── */
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {BORDER_SUBTLE};
    background-color: {BG_INPUT};
}}

QCheckBox::indicator:hover {{
    border: 1px solid {ACCENT_EMERALD};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT_EMERALD};
    border: 1px solid {ACCENT_EMERALD};
}}

/* ─── Console Drawer ─── */
QFrame#ConsoleDrawer {{
    background-color: {BG_DRAWER};
    border-top: 1px solid {BORDER_SUBTLE};
}}

QPlainTextEdit#ConsoleOutput {{
    background-color: {BG_DRAWER};
    color: {ACCENT_EMERALD};
    font-family: "JetBrains Mono", "Fira Code", "Courier New", monospace;
    font-size: 11px;
    border: none;
    padding: 8px;
}}
"""

def add_glow_effect(widget: QWidget, color_hex: str = ACCENT_EMERALD, radius: int = 15):
    """Add a subtle cyber neon glow effect to a widget."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(radius)
    c = QColor(color_hex)
    c.setAlpha(100)
    shadow.setColor(c)
    shadow.setOffset(0, 0)
    widget.setGraphicsEffect(shadow)
