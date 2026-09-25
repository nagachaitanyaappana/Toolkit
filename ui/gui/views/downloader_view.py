"""
Media Downloader View for Toolkit GUI.
Features progressive disclosure:
1. Shows URL input first.
2. Once a valid URL is provided, asynchronously fetches and renders rich video metadata
   (HD thumbnail, title, channel, duration, view count, and real available resolutions).
3. Reveals format options, quality, playlist dropdown, and download controls.
"""

from pathlib import Path
import re
import subprocess

from PyQt6.QtCore import QByteArray, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import requests
import yt_dlp
from core.engine import format_filesize, is_playlist as check_is_playlist, is_spotify_url
from core.options import build_yt_dlp_options
from tools.downloader import detect_platform
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
from utils.paths import get_downloads_dir
from utils.validation import is_valid_url


def format_duration(seconds: int | float | None) -> str:
    """Format duration in seconds into HH:MM:SS or MM:SS."""
    if not seconds:
        return ""
    sec = int(seconds)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m:02d}m {s:02d}s"


def format_views(count: int | None) -> str:
    """Format view count into readable string."""
    if not count:
        return ""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M views"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K views"
    return f"{count:,} views"


class MetadataFetchWorker(QThread):
    metadata_ready = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": "in_playlist",
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)

            title = info.get("title") or "Media Stream"
            uploader = info.get("uploader") or info.get("channel") or info.get("creator") or "Unknown Creator"
            duration = info.get("duration", 0)
            view_count = info.get("view_count", 0)

            # Find best thumbnail URL
            thumb_url = info.get("thumbnail")
            if not thumb_url and info.get("thumbnails"):
                thumb_url = info["thumbnails"][-1].get("url")

            thumb_bytes = None
            if thumb_url:
                try:
                    r = requests.get(thumb_url, timeout=6)
                    if r.status_code == 200:
                        thumb_bytes = r.content
                except Exception:
                    pass

            # Extract available video resolutions
            formats = info.get("formats", [])
            heights = set()
            for f in formats:
                h = f.get("height")
                if h and isinstance(h, int) and h >= 144:
                    heights.add(h)
            sorted_res = [f"{h}p" for h in sorted(heights, reverse=True)]

            result = {
                "title": title,
                "uploader": uploader,
                "duration": duration,
                "view_count": view_count,
                "thumb_bytes": thumb_bytes,
                "resolutions": sorted_res,
                "is_playlist": info.get("_type") == "playlist" or "entries" in info,
            }
            self.metadata_ready.emit(result)
        except Exception as exc:
            self.error_signal.emit(str(exc))


class DownloaderWorker(QThread):
    progress_signal = pyqtSignal(float, str)  # percent, speed
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(
        self,
        url: str,
        download_type: str,
        quality: str,
        output_dir: Path,
        is_playlist: bool = False,
        playlist_range: str = "",
    ):
        super().__init__()
        self.url = url
        self.download_type = download_type
        self.quality = quality
        self.output_dir = output_dir
        self.is_playlist = is_playlist
        self.playlist_range = playlist_range

    def run(self):
        try:
            self.log_signal.emit(f"⚡ Initializing download: {self.url}")

            # Spotify handling via spotdl
            if is_spotify_url(self.url):
                self.log_signal.emit("🎵 Detected Spotify link, launching spotdl...")
                cmd = ["spotdl", "download", self.url, "--output", str(self.output_dir)]
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                for line in proc.stdout:
                    clean = line.strip()
                    if clean:
                        self.log_signal.emit(clean)
                proc.wait()
                if proc.returncode == 0:
                    self.finished_signal.emit(True, "Spotify media downloaded successfully!")
                else:
                    self.finished_signal.emit(
                        False, f"spotdl exited with error code {proc.returncode}"
                    )
                return

            # YouTube & general media handling via yt-dlp
            video_fmt = "mp4"
            audio_fmt = "mp3"

            if self.download_type == "audio":
                audio_fmt = self.quality.lower()
                resolution = "best"
            else:
                clean_q = self.quality.lower().replace("p", "").strip()
                if clean_q in ("best", "best (auto)", "auto", ""):
                    resolution = "best"
                else:
                    resolution = clean_q

            opts = build_yt_dlp_options(
                url=self.url,
                output_dir=self.output_dir,
                video_format=video_fmt,
                audio_format=audio_fmt,
                download_type=self.download_type,
                resolution=resolution,
                is_playlist=self.is_playlist,
            )

            if self.is_playlist and self.playlist_range:
                opts["playlist_items"] = self.playlist_range

            def _hook(d: dict):
                status = d.get("status")
                if status == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    downloaded = d.get("downloaded_bytes", 0)
                    speed = d.get("speed") or 0
                    speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed else "--"
                    pct = (downloaded * 100 / total) if total > 0 else 0.0
                    self.progress_signal.emit(pct, speed_str)

                    filename = Path(d.get("filename", "")).name
                    self.log_signal.emit(f"⬇ {filename} — {pct:.1f}% ({speed_str})")
                elif status == "finished":
                    self.progress_signal.emit(100.0, "Done")
                    self.log_signal.emit("⚙️ Merging streams with FFmpeg...")

            opts["progress_hooks"] = [_hook]

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url])

            self.finished_signal.emit(True, "Media downloaded successfully!")

        except Exception as exc:
            self.log_signal.emit(f"✗ Download failed: {str(exc)}")
            self.finished_signal.emit(False, str(exc))


class DownloaderView(QWidget):
    log_requested = pyqtSignal(str)
    toast_requested = pyqtSignal(str, bool)

    PLAYLIST_CHOICES = [
        ("All Videos / Tracks in Playlist", ""),
        ("First 5 Items (1-5)", "1-5"),
        ("First 10 Items (1-10)", "1-10"),
        ("First 20 Items (1-20)", "1-20"),
        ("First 50 Items (1-50)", "1-50"),
        ("Custom Item Range...", "custom"),
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.worker: DownloaderWorker | None = None
        self.meta_worker: MetadataFetchWorker | None = None
        self.output_dir = get_downloads_dir()
        self.discovered_resolutions: list[str] = []
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Responsive Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title = QLabel("📥 Media Downloader")
        title.setProperty("class", "ViewTitle")
        sub = QLabel(
            "Download high-res video and audio from YouTube, Spotify, Instagram, X/Twitter, Pinterest & Reddit."
        )
        sub.setProperty("class", "ViewSubtitle")
        header_box.addWidget(title)
        header_box.addWidget(sub)
        layout.addLayout(header_box)

        # ─── STEP 1: URL INPUT CARD ───
        self.url_card = QFrame()
        self.url_card.setProperty("class", "CyberCard")
        url_card_layout = QVBoxLayout(self.url_card)
        url_card_layout.setContentsMargins(20, 20, 20, 20)
        url_card_layout.setSpacing(14)

        card_title = QLabel("ENTER MEDIA URL")
        card_title.setProperty("class", "CardTitle")
        url_card_layout.addWidget(card_title)

        url_row = QHBoxLayout()
        url_row.setSpacing(10)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "Paste link (e.g. YouTube, Spotify, Instagram, X/Twitter, Pinterest)..."
        )
        self.url_input.setFixedHeight(40)
        self.url_input.textChanged.connect(self._on_url_typed)
        self.url_input.returnPressed.connect(self._inspect_and_reveal)
        url_row.addWidget(self.url_input)

        paste_btn = QPushButton("📋 Paste")
        paste_btn.setProperty("class", "SecondaryBtn")
        paste_btn.setFixedHeight(40)
        paste_btn.clicked.connect(self._paste_url)
        url_row.addWidget(paste_btn)

        self.inspect_btn = QPushButton("Fetch Media ➔")
        self.inspect_btn.setProperty("class", "PrimaryBtn")
        self.inspect_btn.setFixedHeight(40)
        self.inspect_btn.clicked.connect(self._inspect_and_reveal)
        url_row.addWidget(self.inspect_btn)

        url_card_layout.addLayout(url_row)

        self.detected_label = QLabel("Paste a URL above to inspect video information and download.")
        self.detected_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        url_card_layout.addWidget(self.detected_label)

        layout.addWidget(self.url_card)

        # ─── STEP 2: RICH VIDEO METADATA PREVIEW CARD ───
        self.info_card = QFrame()
        self.info_card.setProperty("class", "CyberCard")
        self.info_card.setStyleSheet(
            f"background-color: {BG_CARD}; border: 1px solid rgba(0, 255, 157, 0.25); border-radius: 12px;"
        )
        info_layout = QHBoxLayout(self.info_card)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(18)

        # Thumbnail Label
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(180, 102)
        self.thumb_label.setStyleSheet(
            f"background-color: {BG_INPUT}; border: 1px solid {BORDER_SUBTLE}; border-radius: 8px;"
        )
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setText("🎬 Preview")
        info_layout.addWidget(self.thumb_label)

        # Video Details Box
        details_box = QVBoxLayout()
        details_box.setSpacing(6)

        self.video_title_label = QLabel("Loading media details...")
        self.video_title_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 15px; font-weight: 800;"
        )
        self.video_title_label.setWordWrap(True)
        details_box.addWidget(self.video_title_label)

        # Badges row (Channel, Duration, Views, Platform)
        self.badges_row = QHBoxLayout()
        self.badges_row.setSpacing(8)

        self.channel_badge = QLabel("👤 Channel")
        self.channel_badge.setStyleSheet(
            f"color: {ACCENT_CYAN}; font-size: 11px; font-weight: 700; background: rgba(0,229,255,0.08); padding: 3px 8px; border-radius: 4px;"
        )
        self.badges_row.addWidget(self.channel_badge)

        self.duration_badge = QLabel("⏱️ Duration")
        self.duration_badge.setStyleSheet(
            f"color: {ACCENT_EMERALD}; font-size: 11px; font-weight: 700; background: rgba(0,255,157,0.08); padding: 3px 8px; border-radius: 4px;"
        )
        self.badges_row.addWidget(self.duration_badge)

        self.views_badge = QLabel("👁️ Views")
        self.views_badge.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 700; background: rgba(255,255,255,0.05); padding: 3px 8px; border-radius: 4px;"
        )
        self.badges_row.addWidget(self.views_badge)

        self.platform_badge = QLabel("YOUTUBE")
        self.platform_badge.setStyleSheet(
            f"color: #ff4444; font-size: 10px; font-weight: 800; background: rgba(255,68,68,0.12); border: 1px solid rgba(255,68,68,0.3); padding: 3px 8px; border-radius: 4px;"
        )
        self.badges_row.addWidget(self.platform_badge)
        self.badges_row.addStretch()

        details_box.addLayout(self.badges_row)
        info_layout.addLayout(details_box, 1)

        layout.addWidget(self.info_card)
        self.info_card.hide()

        # ─── STEP 3: DOWNLOAD CONFIGURATION CARD ───
        self.options_card = QFrame()
        self.options_card.setProperty("class", "CyberCard")
        options_layout = QVBoxLayout(self.options_card)
        options_layout.setContentsMargins(20, 20, 20, 20)
        options_layout.setSpacing(16)

        opt_title = QLabel("SELECT FORMAT & OPTIONS")
        opt_title.setProperty("class", "CardTitle")
        options_layout.addWidget(opt_title)

        # Settings Grid: Media Type & Quality
        settings_row = QHBoxLayout()
        settings_row.setSpacing(16)

        # Format Type (Video vs Audio)
        type_box = QVBoxLayout()
        type_box.setSpacing(6)
        type_box.addWidget(QLabel("Media Format:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Video (MP4)", "Audio Only (MP3/FLAC)"])
        self.type_combo.currentIndexChanged.connect(self._update_quality_options)
        self.type_combo.setFixedHeight(36)
        type_box.addWidget(self.type_combo)
        settings_row.addLayout(type_box)

        # Quality
        qual_box = QVBoxLayout()
        qual_box.setSpacing(6)
        qual_box.addWidget(QLabel("Quality / Codec:"))
        self.qual_combo = QComboBox()
        self.qual_combo.setFixedHeight(36)
        qual_box.addWidget(self.qual_combo)
        settings_row.addLayout(qual_box)

        options_layout.addLayout(settings_row)

        # Playlist Configuration with Dropdown
        self.playlist_container = QWidget()
        pl_layout = QVBoxLayout(self.playlist_container)
        pl_layout.setContentsMargins(0, 4, 0, 4)
        pl_layout.setSpacing(8)

        self.playlist_cb = QCheckBox("Download as Playlist / Album")
        self.playlist_cb.toggled.connect(self._toggle_playlist_options)
        pl_layout.addWidget(self.playlist_cb)

        pl_sub_row = QHBoxLayout()
        pl_sub_row.setSpacing(10)

        pl_sub_row.addWidget(QLabel("Items to Download:"))
        self.playlist_combo = QComboBox()
        for label, val in self.PLAYLIST_CHOICES:
            self.playlist_combo.addItem(label, val)
        self.playlist_combo.setEnabled(False)
        self.playlist_combo.setFixedHeight(34)
        self.playlist_combo.currentIndexChanged.connect(self._on_playlist_choice_changed)
        pl_sub_row.addWidget(self.playlist_combo, 2)

        self.custom_range_input = QLineEdit()
        self.custom_range_input.setPlaceholderText("e.g. 1-15, 20")
        self.custom_range_input.setFixedWidth(130)
        self.custom_range_input.setFixedHeight(34)
        self.custom_range_input.hide()
        pl_sub_row.addWidget(self.custom_range_input)

        pl_layout.addLayout(pl_sub_row)
        options_layout.addWidget(self.playlist_container)

        # Destination Folder Row
        dest_row = QHBoxLayout()
        dest_row.setSpacing(10)
        dest_label = QLabel("Output Folder:")
        dest_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        dest_row.addWidget(dest_label)

        self.dir_label = QLabel(str(self.output_dir))
        self.dir_label.setStyleSheet(f"color: {ACCENT_CYAN}; font-weight: 600; font-size: 12px;")
        dest_row.addWidget(self.dir_label)
        dest_row.addStretch()

        browse_btn = QPushButton("📁 Browse")
        browse_btn.setProperty("class", "SecondaryBtn")
        browse_btn.setFixedHeight(30)
        browse_btn.clicked.connect(self._choose_folder)
        dest_row.addWidget(browse_btn)
        options_layout.addLayout(dest_row)

        # Action Button & Progress
        options_layout.addSpacing(6)
        self.download_btn = QPushButton("⚡ START DOWNLOAD")
        self.download_btn.setProperty("class", "PrimaryBtn")
        self.download_btn.setFixedHeight(44)
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.clicked.connect(self._start_download)
        options_layout.addWidget(self.download_btn)

        # Progress Area
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        options_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready for download.")
        self.status_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        options_layout.addWidget(self.status_label)

        layout.addWidget(self.options_card)
        self.options_card.hide()

        layout.addStretch()
        scroll.setWidget(scroll_content)
        root_layout.addWidget(scroll)

        self._update_quality_options(0)

    def _paste_url(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            text = clipboard.text().strip()
            self.url_input.setText(text)
            self._inspect_and_reveal()

    def _on_url_typed(self, text: str):
        cleaned = text.strip()
        if not cleaned:
            self.info_card.hide()
            self.options_card.hide()
            self.detected_label.setText("Paste a URL above to inspect video information and download.")
            return

        if is_valid_url(cleaned):
            self._inspect_and_reveal()

    def _inspect_and_reveal(self):
        url = self.url_input.text().strip()
        if not url:
            self.toast_requested.emit("Please enter a media URL.", True)
            return

        platform = detect_platform(url)
        is_pl = check_is_playlist(url)

        self.platform_badge.setText(platform.upper())

        # Platform specific styling
        if platform == "youtube":
            self.platform_badge.setStyleSheet("color: #ff4444; font-size: 10px; font-weight: 800; background: rgba(255,68,68,0.12); border: 1px solid rgba(255,68,68,0.3); padding: 3px 8px; border-radius: 4px;")
        elif platform == "spotify":
            self.platform_badge.setStyleSheet(f"color: {ACCENT_EMERALD}; font-size: 10px; font-weight: 800; background: rgba(0,255,157,0.12); border: 1px solid {ACCENT_EMERALD}; padding: 3px 8px; border-radius: 4px;")
        else:
            self.platform_badge.setStyleSheet(f"color: {ACCENT_CYAN}; font-size: 10px; font-weight: 800; background: rgba(0,229,255,0.12); border: 1px solid {ACCENT_CYAN}; padding: 3px 8px; border-radius: 4px;")

        if is_pl:
            self.playlist_cb.setChecked(True)
            self.playlist_combo.setEnabled(True)
            self.detected_label.setText(f"✓ Detected {platform.capitalize()} Playlist!")
        else:
            self.playlist_cb.setChecked(False)
            self.playlist_combo.setEnabled(False)
            self.detected_label.setText(f"✓ Detected {platform.capitalize()} media.")

        # Show info card with loading state
        self.video_title_label.setText(f"⏳ Fetching {platform.capitalize()} media information...")
        self.channel_badge.setText("👤 Loading channel...")
        self.duration_badge.setText("⏱️ Loading...")
        self.views_badge.setText("👁️ Loading...")
        self.thumb_label.setText("⏳ Loading...")
        self.info_card.show()
        self.options_card.show()

        # Start asynchronous metadata fetch
        self.inspect_btn.setEnabled(False)
        self.meta_worker = MetadataFetchWorker(url)
        self.meta_worker.metadata_ready.connect(self._on_metadata_ready)
        self.meta_worker.error_signal.connect(self._on_metadata_error)
        self.meta_worker.start()

    def _on_metadata_ready(self, meta: dict):
        self.inspect_btn.setEnabled(True)
        title = meta.get("title", "Media Video")
        uploader = meta.get("uploader", "Unknown Channel")
        duration_sec = meta.get("duration", 0)
        views = meta.get("view_count", 0)
        thumb_bytes = meta.get("thumb_bytes")
        resolutions = meta.get("resolutions", [])

        self.video_title_label.setText(title)
        self.channel_badge.setText(f"👤 {uploader}")

        dur_text = format_duration(duration_sec)
        if dur_text:
            self.duration_badge.setText(f"⏱️ {dur_text}")
            self.duration_badge.show()
        else:
            self.duration_badge.hide()

        views_text = format_views(views)
        if views_text:
            self.views_badge.setText(f"👁️ {views_text}")
            self.views_badge.show()
        else:
            self.views_badge.hide()

        # Load Thumbnail image
        if thumb_bytes:
            qimg = QImage()
            if qimg.loadFromData(thumb_bytes):
                pix = QPixmap.fromImage(qimg).scaled(
                    180, 102, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
                )
                self.thumb_label.setPixmap(pix)
            else:
                self.thumb_label.setText("🎬 Preview")
        else:
            self.thumb_label.setText("🎬 Preview")

        # Save discovered resolutions and update dropdown
        if resolutions:
            self.discovered_resolutions = resolutions
            self._update_quality_options(self.type_combo.currentIndex())

        self.toast_requested.emit(f"Loaded: {title[:40]}...", False)

    def _on_metadata_error(self, err: str):
        self.inspect_btn.setEnabled(True)
        self.video_title_label.setText("Media Stream Ready")
        self.channel_badge.setText("👤 Media Source")
        self.duration_badge.setText("⏱️ Live / Stream")
        self.views_badge.hide()
        self.thumb_label.setText("🎬 Ready")

    def _toggle_playlist_options(self, checked: bool):
        self.playlist_combo.setEnabled(checked)
        if not checked:
            self.custom_range_input.hide()
        else:
            if self.playlist_combo.currentData() == "custom":
                self.custom_range_input.show()

    def _on_playlist_choice_changed(self, index: int):
        val = self.playlist_combo.currentData()
        if val == "custom":
            self.custom_range_input.show()
            self.custom_range_input.setFocus()
        else:
            self.custom_range_input.hide()

    def _choose_folder(self):
        chosen = QFileDialog.getExistingDirectory(
            self, "Select Download Directory", str(self.output_dir)
        )
        if chosen:
            self.output_dir = Path(chosen)
            self.dir_label.setText(str(self.output_dir))

    def _update_quality_options(self, index: int):
        self.qual_combo.clear()
        if index == 0:  # Video
            items = ["Best (Auto)"]
            if self.discovered_resolutions:
                items.extend(self.discovered_resolutions)
            else:
                items.extend(["1080p", "720p", "480p", "360p"])
            self.qual_combo.addItems(items)
        else:  # Audio
            self.qual_combo.addItems(["MP3", "M4A", "FLAC", "WAV", "OPUS"])

    def _start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.toast_requested.emit("Please enter a media URL.", True)
            return

        is_audio = self.type_combo.currentIndex() == 1
        download_type = "audio" if is_audio else "video"
        quality = self.qual_combo.currentText()
        is_playlist = self.playlist_cb.isChecked()

        playlist_range = ""
        if is_playlist:
            choice = self.playlist_combo.currentData()
            if choice == "custom":
                playlist_range = self.custom_range_input.text().strip()
            else:
                playlist_range = choice or ""

        self.download_btn.setEnabled(False)
        self.download_btn.setText("⏳ DOWNLOADING...")
        self.progress_bar.setValue(0)
        self.status_label.setText("Initializing download engine...")

        self.worker = DownloaderWorker(
            url=url,
            download_type=download_type,
            quality=quality,
            output_dir=self.output_dir,
            is_playlist=is_playlist,
            playlist_range=playlist_range,
        )
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.log_signal.connect(self.log_requested.emit)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, percent: float, speed: str):
        self.progress_bar.setValue(int(percent))
        self.status_label.setText(f"Downloading: {percent:.1f}% ({speed})")

    def _on_finished(self, success: bool, message: str):
        self.download_btn.setEnabled(True)
        self.download_btn.setText("⚡ START DOWNLOAD")
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText(f"✓ {message}")
            self.toast_requested.emit(message, False)
        else:
            self.status_label.setText(f"✗ Failed: {message}")
            self.toast_requested.emit(f"Error: {message}", True)
