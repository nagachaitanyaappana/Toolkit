"""
QR Code Studio View for Toolkit GUI.
Real-time QR code generation, customizable colors and presets,
high-res preview rendering, file export, and instant clipboard copying.
"""

import io
from pathlib import Path

from PIL import Image
import qrcode
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from utils.paths import get_downloads_dir
from ui.gui.theme import (
    ACCENT_CYAN,
    ACCENT_EMERALD,
    BG_CARD,
    BG_INPUT,
    BORDER_SUBTLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class QRView(QWidget):
    toast_requested = pyqtSignal(str, bool)
    log_requested = pyqtSignal(str)

    COLOR_PRESETS = {
        "Matrix Emerald": ("#00ff9d", "#090d12"),
        "Cyber Cyan": ("#00e5ff", "#0c131b"),
        "Classic Dark": ("#000000", "#ffffff"),
        "Inverted Monokai": ("#ffffff", "#1e1e1e"),
        "Neon Purple": ("#c084fc", "#0f0d1b"),
    }

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.fg_color = "#00ff9d"
        self.bg_color = "#090d12"
        self.current_pil_img: Image.Image | None = None
        self._init_ui()
        self._generate_qr()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title = QLabel("🏁 QR Code Studio")
        title.setProperty("class", "ViewTitle")
        sub = QLabel("Generate high-contrast, customizable QR codes in real-time with PNG and clipboard export.")
        sub.setProperty("class", "ViewSubtitle")
        header_box.addWidget(title)
        header_box.addWidget(sub)
        layout.addLayout(header_box)

        # Content Split Layout
        split_layout = QHBoxLayout()
        split_layout.setSpacing(20)

        # ─── Left Configuration Panel ───
        config_card = QFrame()
        config_card.setProperty("class", "CyberCard")
        cfg_layout = QVBoxLayout(config_card)
        cfg_layout.setContentsMargins(20, 20, 20, 20)
        cfg_layout.setSpacing(14)

        cfg_title = QLabel("CONTENT & PARAMETERS")
        cfg_title.setProperty("class", "CardTitle")
        cfg_layout.addWidget(cfg_title)

        # Input data
        self.data_input = QTextEdit()
        self.data_input.setPlaceholderText("Enter URL, Wi-Fi configuration, or text to encode...")
        self.data_input.setText("https://github.com/nagachaitanyaappana")
        self.data_input.setFixedHeight(80)
        self.data_input.textChanged.connect(self._generate_qr)
        cfg_layout.addWidget(self.data_input)

        # Theme preset picker
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Color Theme:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.COLOR_PRESETS.keys()))
        self.preset_combo.currentTextChanged.connect(self._apply_preset)
        self.preset_combo.setFixedHeight(34)
        preset_row.addWidget(self.preset_combo)
        cfg_layout.addLayout(preset_row)

        # Custom Colors Row
        color_row = QHBoxLayout()
        self.fg_btn = QPushButton("Foreground Color")
        self.fg_btn.setProperty("class", "SecondaryBtn")
        self.fg_btn.clicked.connect(self._pick_fg)
        color_row.addWidget(self.fg_btn)

        self.bg_btn = QPushButton("Background Color")
        self.bg_btn.setProperty("class", "SecondaryBtn")
        self.bg_btn.clicked.connect(self._pick_bg)
        color_row.addWidget(self.bg_btn)
        cfg_layout.addLayout(color_row)

        # Sliders (Box Size & Error Correction)
        slider_row = QHBoxLayout()
        self.size_label = QLabel("Scale: 10px")
        self.size_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(4, 20)
        self.size_slider.setValue(10)
        self.size_slider.valueChanged.connect(self._on_scale_change)
        slider_row.addWidget(self.size_label)
        slider_row.addWidget(self.size_slider)
        cfg_layout.addLayout(slider_row)

        ec_row = QHBoxLayout()
        ec_row.addWidget(QLabel("Error Correction:"))
        self.ec_combo = QComboBox()
        self.ec_combo.addItems(["Low (7%)", "Medium (15%)", "Quartile (25%)", "High (30%)"])
        self.ec_combo.setCurrentIndex(1)
        self.ec_combo.currentIndexChanged.connect(self._generate_qr)
        self.ec_combo.setFixedHeight(34)
        ec_row.addWidget(self.ec_combo)
        cfg_layout.addLayout(ec_row)

        cfg_layout.addStretch()

        # Action Buttons
        btn_box = QHBoxLayout()
        self.copy_btn = QPushButton("📋 Copy Image")
        self.copy_btn.setProperty("class", "SecondaryBtn")
        self.copy_btn.setFixedHeight(38)
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_box.addWidget(self.copy_btn)

        self.save_btn = QPushButton("💾 Save PNG")
        self.save_btn.setProperty("class", "PrimaryBtn")
        self.save_btn.setFixedHeight(38)
        self.save_btn.clicked.connect(self._save_image)
        btn_box.addWidget(self.save_btn)

        cfg_layout.addLayout(btn_box)

        split_layout.addWidget(config_card, 1)

        # ─── Right Preview Canvas Panel ───
        preview_card = QFrame()
        preview_card.setProperty("class", "CyberCard")
        pv_layout = QVBoxLayout(preview_card)
        pv_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pv_layout.setContentsMargins(20, 20, 20, 20)
        pv_layout.setSpacing(12)

        pv_title = QLabel("LIVE CODE PREVIEW")
        pv_title.setProperty("class", "CardTitle")
        pv_layout.addWidget(pv_title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setFixedSize(300, 300)
        self.qr_label.setStyleSheet(
            f"border: 2px dashed rgba(0, 255, 157, 0.3); border-radius: 12px; background: {BG_INPUT};"
        )
        pv_layout.addWidget(self.qr_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.dim_label = QLabel("300 × 300 px")
        self.dim_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        pv_layout.addWidget(self.dim_label, alignment=Qt.AlignmentFlag.AlignCenter)

        split_layout.addWidget(preview_card, 1)

        layout.addLayout(split_layout)
        layout.addStretch()

        scroll.setWidget(scroll_content)
        root_layout.addWidget(scroll)

    def _on_scale_change(self, val: int):
        self.size_label.setText(f"Scale: {val}px")
        self._generate_qr()

    def _apply_preset(self, text: str):
        if text in self.COLOR_PRESETS:
            self.fg_color, self.bg_color = self.COLOR_PRESETS[text]
            self._generate_qr()

    def _pick_fg(self):
        color = QColorDialog.getColor(QColor(self.fg_color), self, "Select Foreground Color")
        if color.isValid():
            self.fg_color = color.name()
            self._generate_qr()

    def _pick_bg(self):
        color = QColorDialog.getColor(QColor(self.bg_color), self, "Select Background Color")
        if color.isValid():
            self.bg_color = color.name()
            self._generate_qr()

    def _generate_qr(self):
        data = self.data_input.toPlainText().strip()
        if not data:
            self.qr_label.clear()
            self.qr_label.setText("Enter text to preview QR")
            return

        ec_map = [ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H]
        ec_level = ec_map[self.ec_combo.currentIndex()]
        scale = self.size_slider.value()

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=ec_level,
                box_size=scale,
                border=2,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color=self.fg_color, back_color=self.bg_color).convert("RGBA")
            self.current_pil_img = img

            # Convert PIL to QPixmap
            data_bytes = img.tobytes("raw", "RGBA")
            qim = QImage(data_bytes, img.size[0], img.size[1], QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qim)

            scaled_pixmap = pixmap.scaled(
                280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.qr_label.setPixmap(scaled_pixmap)
            self.dim_label.setText(f"{img.width} × {img.height} px")

        except Exception as exc:
            self.qr_label.setText(f"Error: {exc}")

    def _copy_to_clipboard(self):
        if not self.current_pil_img:
            return
        clipboard = QApplication.clipboard()
        if clipboard and self.qr_label.pixmap():
            # Create full-res pixmap from PIL image
            img = self.current_pil_img
            data_bytes = img.tobytes("raw", "RGBA")
            qim = QImage(data_bytes, img.size[0], img.size[1], QImage.Format.Format_RGBA8888)
            pix = QPixmap.fromImage(qim)
            clipboard.setPixmap(pix)
            self.toast_requested.emit("QR Code image copied to clipboard!", False)

    def _save_image(self):
        if not self.current_pil_img:
            return

        default_path = str(get_downloads_dir() / "qrcode.png")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save QR Code", default_path, "PNG Images (*.png);;All Files (*)"
        )
        if file_path:
            try:
                self.current_pil_img.save(file_path)
                self.toast_requested.emit(f"Saved: {Path(file_path).name}", False)
                self.log_requested.emit(f"✓ QR Code saved to: {file_path}")
            except Exception as exc:
                self.toast_requested.emit(f"Failed to save: {exc}", True)
