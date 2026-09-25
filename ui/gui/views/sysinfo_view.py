"""
System Telemetry & Hardware Monitor View for Toolkit GUI.
Real-time CPU, RAM, Swap, Disk gauges, and OS kernel telemetry with Cyberpunk aesthetics.
"""

from datetime import datetime
import platform

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import psutil
from ui.gui.theme import (
    ACCENT_CYAN,
    ACCENT_EMERALD,
    ACCENT_WARN,
    BG_CARD,
    BG_INPUT,
    BG_SURFACE,
    BORDER_SUBTLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def _fmt(size_bytes: int | float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


class SysInfoView(QWidget):
    toast_requested = pyqtSignal(str, bool)
    log_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.core_bars: list[QProgressBar] = []
        self._init_ui()

        # Live poll timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_telemetry)
        self.timer.start(1500)
        self._update_telemetry()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(28, 28, 28, 28)
        root_layout.setSpacing(16)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title = QLabel("📊 System Telemetry & Hardware Monitor")
        title.setProperty("class", "ViewTitle")
        sub = QLabel("Real-time telemetry for CPU cores, RAM, swap space, mounted partitions, and OS kernel.")
        sub.setProperty("class", "ViewSubtitle")
        header_box.addWidget(title)
        header_box.addWidget(sub)
        root_layout.addLayout(header_box)

        # Scroll area for clean display
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(18)

        # Top 4 Metric Cards Grid
        metrics_grid = QHBoxLayout()
        metrics_grid.setSpacing(14)

        # CPU Card
        self.cpu_card = self._create_metric_card("CPU USAGE", "0%", "Cores: ...")
        metrics_grid.addWidget(self.cpu_card["frame"])

        # RAM Card
        self.ram_card = self._create_metric_card("RAM USAGE", "0%", "... / ...")
        metrics_grid.addWidget(self.ram_card["frame"])

        # Swap Card
        self.swap_card = self._create_metric_card("SWAP USAGE", "0%", "... / ...")
        metrics_grid.addWidget(self.swap_card["frame"])

        # Disk Card
        self.disk_card = self._create_metric_card("ROOT STORAGE", "0%", "... Free")
        metrics_grid.addWidget(self.disk_card["frame"])

        layout.addLayout(metrics_grid)

        # Middle: Per-Core Utilization Card
        cores_card = QFrame()
        cores_card.setProperty("class", "CyberCard")
        cores_layout = QVBoxLayout(cores_card)
        cores_layout.setContentsMargins(18, 16, 18, 16)
        cores_layout.setSpacing(12)

        cores_header = QHBoxLayout()
        cores_title = QLabel("⚡ PER-CORE CPU UTILIZATION")
        cores_title.setProperty("class", "CardTitle")
        cores_header.addWidget(cores_title)
        cores_header.addStretch()

        self.freq_label = QLabel("Freq: - MHz")
        self.freq_label.setStyleSheet(f"color: {ACCENT_CYAN}; font-size: 11px; font-weight: 700;")
        cores_header.addWidget(self.freq_label)
        cores_layout.addLayout(cores_header)

        # Grid of core bars
        self.cores_grid = QGridLayout()
        self.cores_grid.setHorizontalSpacing(16)
        self.cores_grid.setVerticalSpacing(8)

        core_count = psutil.cpu_count(logical=True) or 4
        cols = 4 if core_count >= 8 else 2

        for i in range(core_count):
            r = i // cols
            c = (i % cols) * 2

            lbl = QLabel(f"Core {i}:")
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
            bar = QProgressBar()
            bar.setFixedHeight(12)
            bar.setRange(0, 100)
            bar.setValue(0)
            self.core_bars.append(bar)

            self.cores_grid.addWidget(lbl, r, c)
            self.cores_grid.addWidget(bar, r, c + 1)

        cores_layout.addLayout(self.cores_grid)
        layout.addWidget(cores_card)

        # Bottom Split: System Specs + Disk Table
        split_box = QHBoxLayout()
        split_box.setSpacing(16)

        # System Hardware Specs Card
        specs_card = QFrame()
        specs_card.setProperty("class", "CyberCard")
        specs_layout = QVBoxLayout(specs_card)
        specs_layout.setContentsMargins(18, 16, 18, 16)
        specs_layout.setSpacing(10)

        specs_title = QLabel("🖥️ PLATFORM & HOST SPECS")
        specs_title.setProperty("class", "CardTitle")
        specs_layout.addWidget(specs_title)

        uname = platform.uname()
        boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")

        spec_grid = QGridLayout()
        spec_grid.setHorizontalSpacing(12)
        spec_grid.setVerticalSpacing(6)

        specs = [
            ("Operating System", uname.system),
            ("Hostname / Node", uname.node),
            ("Kernel Release", uname.release),
            ("Architecture", uname.machine),
            ("Physical Cores", str(psutil.cpu_count(logical=False))),
            ("Logical Threads", str(psutil.cpu_count(logical=True))),
            ("Boot Timestamp", boot_time),
            ("Python Version", platform.python_version()),
        ]

        for idx, (k, v) in enumerate(specs):
            lbl_k = QLabel(k)
            lbl_k.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
            lbl_v = QLabel(v)
            lbl_v.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: 600; font-size: 11px;")
            spec_grid.addWidget(lbl_k, idx, 0)
            spec_grid.addWidget(lbl_v, idx, 1)

        specs_layout.addLayout(spec_grid)
        specs_layout.addStretch()
        split_box.addWidget(specs_card, 1)

        # Disks Table Card
        disk_card = QFrame()
        disk_card.setProperty("class", "CyberCard")
        disk_layout = QVBoxLayout(disk_card)
        disk_layout.setContentsMargins(18, 16, 18, 16)
        disk_layout.setSpacing(10)

        disk_title = QLabel("💾 STORAGE PARTITIONS")
        disk_title.setProperty("class", "CardTitle")
        disk_layout.addWidget(disk_title)

        self.disk_table = QTableWidget()
        self.disk_table.setColumnCount(5)
        self.disk_table.setHorizontalHeaderLabels(["MOUNT", "FS", "TOTAL", "FREE", "USAGE"])
        self.disk_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.disk_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.disk_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.disk_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.disk_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.disk_table.setColumnWidth(4, 80)
        self.disk_table.verticalHeader().setVisible(False)
        self.disk_table.setFixedHeight(180)
        disk_layout.addWidget(self.disk_table)

        split_box.addWidget(disk_card, 1)
        layout.addLayout(split_box)

        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll)

    def _create_metric_card(self, label: str, default_val: str, sub: str) -> dict:
        frame = QFrame()
        frame.setProperty("class", "CyberCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setProperty("class", "MetricLabel")
        layout.addWidget(lbl)

        val = QLabel(default_val)
        val.setProperty("class", "MetricValue")
        layout.addWidget(val)

        sub_lbl = QLabel(sub)
        sub_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(sub_lbl)

        return {"frame": frame, "value": val, "sub": sub_lbl}

    def _update_telemetry(self):
        # 1. CPU
        cpu_pct = psutil.cpu_percent(interval=None)
        self.cpu_card["value"].setText(f"{cpu_pct:.1f}%")
        self.cpu_card["sub"].setText(f"{psutil.cpu_count(logical=True)} Threads active")

        freq = psutil.cpu_freq()
        if freq:
            self.freq_label.setText(f"Freq: {freq.current:.0f} MHz")

        # Per core
        core_pcts = psutil.cpu_percent(percpu=True)
        for i, pct in enumerate(core_pcts):
            if i < len(self.core_bars):
                self.core_bars[i].setValue(int(pct))

        # 2. RAM
        vm = psutil.virtual_memory()
        self.ram_card["value"].setText(f"{vm.percent:.1f}%")
        self.ram_card["sub"].setText(f"{_fmt(vm.used)} / {_fmt(vm.total)}")

        # 3. Swap
        sm = psutil.swap_memory()
        if sm.total:
            self.swap_card["value"].setText(f"{sm.percent:.1f}%")
            self.swap_card["sub"].setText(f"{_fmt(sm.used)} / {_fmt(sm.total)}")
        else:
            self.swap_card["value"].setText("0%")
            self.swap_card["sub"].setText("No Swap Partition")

        # 4. Root Disk
        try:
            du = psutil.disk_usage("/")
            self.disk_card["value"].setText(f"{du.percent:.1f}%")
            self.disk_card["sub"].setText(f"{_fmt(du.free)} Free of {_fmt(du.total)}")
        except Exception:
            pass

        # Partitions Table
        parts = psutil.disk_partitions(all=False)
        self.disk_table.setRowCount(len(parts))
        for r, p in enumerate(parts):
            try:
                u = psutil.disk_usage(p.mountpoint)
                self.disk_table.setItem(r, 0, QTableWidgetItem(p.mountpoint))
                self.disk_table.setItem(r, 1, QTableWidgetItem(p.fstype))
                self.disk_table.setItem(r, 2, QTableWidgetItem(_fmt(u.total)))
                self.disk_table.setItem(r, 3, QTableWidgetItem(_fmt(u.free)))
                pct_item = QTableWidgetItem(f"{u.percent:.1f}%")
                if u.percent > 85:
                    pct_item.setForeground(Qt.GlobalColor.red)
                self.disk_table.setItem(r, 4, pct_item)
            except Exception:
                pass
