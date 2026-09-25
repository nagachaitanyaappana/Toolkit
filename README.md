# ⚡ Toolkit — Cyber Matrix Developer & Media Control Center

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PyQt6-00ff9d.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-cyan.svg)](https://github.com/nagachaitanyaappana/Toolkit/releases)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

**Toolkit** is a fast, responsive, native desktop application and CLI control center styled in an aesthetic **Cyberpunk / Emerald Matrix** dark design language. Built with Python and PyQt6 for Linux and Windows, it consolidates essential everyday developer utilities, media downloaders, encryption vaults, and telemetry into a single high-performance cockpit.

---

## 🌟 Key Features

### 📥 1. High-Performance Media Downloader
- **Multi-Platform Support**: YouTube, Spotify (`spotdl`), Instagram, X/Twitter, Pinterest, and Reddit.
- **Rich Live Metadata Preview**: Displays HD video thumbnails, full titles, channels/uploaders, duration counters, and live view counts before downloading.
- **Smart Quality Selector**: Automatically queries video streams and populates the quality dropdown with real, available resolutions (e.g. `1080p`, `720p`, `480p`, `Best (Auto)`).
- **Audio Extraction**: 1-click audio stripping to MP3 (320kbps), M4A, FLAC, WAV, and OPUS with FFmpeg.
- **Playlist Manager**: Auto-detects playlists and albums with an item range selector dropdown (`All`, `1-5`, `1-10`, `1-20`, `1-50`, or `Custom`).
- **Live Stream Tracking**: Non-blocking progress bars, streaming download speeds, and real-time logs.

### 🔐 2. Encrypted Password Vault & Generator
- **Military-Grade Encryption**: AES-256 Fernet encryption with PBKDF2 HMAC-SHA256 (100,000 iterations).
- **Searchable Credentials**: Instant client-side search across services, usernames, and notes.
- **1-Click Clipboard Actions**: Quick-copy passwords and usernames with auto-clearing feedback toasts.
- **Built-in Entropy Generator**: Cryptographically secure password generation with length sliders (8 to 64 chars) and custom symbol character pools.

### 📱 3. Phone & Truecaller Intelligence
- **International Number Parsing**: Standardizes input to E.164, national, and international formats via `phonenumbers`.
- **Telecom & Geolocation**: Detects carrier networks, country/region locations, timezones, and line types (Mobile vs Landline).
- **WhatsApp Web Integration**: 1-click button to jump directly into a WhatsApp chat without saving the contact.
- **Truecaller Caller ID & Spam Risk**: Queries Truecaller API for registered names, spam percentage risk scores, and spam classifications.

### 🏁 4. QR Code Studio
- **Real-Time Reactive Generator**: Live code generation as you type text, Wi-Fi keys, or URLs.
- **Matrix & Cyber Color Themes**: Presets for Matrix Emerald (`#00ff9d`), Cyber Cyan, Classic Dark, Inverted Monokai, and custom RGB color pickers.
- **Export Options**: 1-click "Save to PNG" and "Copy Image to Clipboard".

### 📨 5. Gmail & Message Dispatcher
- **Secure Persistent Sessions**: Stores credentials safely using Google App Passwords over direct SSL (`smtp.gmail.com:465`).
- **Multi-Recipient Broadcasting**: Send to multiple addresses separated by commas, semicolons, or newlines.
- **Repeat Batch Multiplier**: Send multiple messages (1 to 100 repeats) with adjustable interval safety delays (1s, 2s, 5s, 10s) and a live cancellation button.
- **Scheduled Delayed Dispatch**: Send immediately or schedule delivery for later (`In 1 min`, `5 min`, `15 min`, `1 hour`, or a custom Date & Time picker) with a live countdown timer.
- **Prebuilt Templates**: Notification alerts, verification codes, meeting reminders, and custom follow-ups.

### 📊 6. System Telemetry & Hardware Monitor
- **Live Metric Gauges**: Real-time polling for CPU utilization, RAM usage, Swap space, and Root storage.
- **Per-Core Utilization**: Visual emerald progress meters for all individual CPU cores.
- **Hardware & Kernel Specs**: OS release, kernel version, CPU frequency, uptime, and architecture.
- **Storage Partitions Table**: Live overview of all mounted drives, file systems, and remaining capacity.

### 📟 7. Real-Time Console Drawer
- Collapsible bottom terminal drawer (`Ctrl + L`) streaming live logs, download progress, and transmission metrics.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + 1` | Switch to Media Downloader |
| `Ctrl + 2` | Switch to Password Vault |
| `Ctrl + 3` | Switch to Phone Checker |
| `Ctrl + 4` | Switch to QR Code Studio |
| `Ctrl + 5` | Switch to Message Dispatcher |
| `Ctrl + 6` | Switch to System Telemetry |
| `Ctrl + L` | Toggle Live Console Drawer |
| `Ctrl + B` | Toggle Compact / Expanded Sidebar |
| `Ctrl + Q` | Quit Application |

---

## 📦 Download Pre-built Binaries

Ready-to-use standalone executables for Linux and Windows are available on the **[GitHub Releases](https://github.com/nagachaitanyaappana/Toolkit/releases)** page:

| Platform | Package | Description |
| :--- | :--- | :--- |
| **Linux (x86_64)** | `Toolkit-linux-x86_64.tar.gz` | Standalone executable + `.desktop` launcher & icon |
| **Windows (x64)** | `Toolkit-windows-x64.zip` | Standalone `Toolkit.exe` |

---

## 🚀 Installation & Setup Guide

### Prerequisites
- **Python 3.10** or higher
- **FFmpeg** (required for video/audio stream merging and format conversions)
- **Git**

---

### 🐧 Linux Setup

#### 1. Install System Dependencies & FFmpeg
- **Arch Linux / Manjaro / EndeavourOS**:
  ```bash
  sudo pacman -S python python-pip ffmpeg git
  ```
- **Ubuntu / Debian / Pop!_OS / Linux Mint**:
  ```bash
  sudo apt update && sudo apt install -y python3 python3-pip ffmpeg git
  ```
- **Fedora**:
  ```bash
  sudo dnf install -y python3 python3-pip ffmpeg git
  ```

#### 2. Clone and Install Python Dependencies
```bash
git clone https://github.com/nagachaitanyaappana/Toolkit.git
cd Toolkit

# Install Python requirements
pip install -r requirements.txt
```

#### 3. Launch Toolkit
```bash
# Launch the PyQt6 Desktop GUI
python3 main.py
# or using the executable wrapper
./toolkit

# Launch the Terminal TUI Mode
./toolkit --cli
```

#### 4. Add Desktop Entry (Application Menu & Dock)
To pin Toolkit to your desktop dock (e.g. COSMIC, GNOME, KDE):
```bash
# Install desktop entry
cp toolkit.desktop ~/.local/share/applications/
chmod +x ~/.local/share/applications/toolkit.desktop

# Update desktop database
update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
```

---

### 🪟 Windows Setup

#### 1. Install Python & FFmpeg
1. Download and install **Python 3.10+** from [python.org](https://www.python.org/downloads/) (make sure to check **"Add Python to PATH"** during installation).
2. Install **FFmpeg**:
   - Using **Winget** (PowerShell as Administrator):
     ```powershell
     winget install Gyan.FFmpeg
     ```
   - Or using **Chocolatey**:
     ```powershell
     choco install ffmpeg
     ```

#### 2. Clone and Install Dependencies
Open **Command Prompt** or **PowerShell**:
```powershell
git clone https://github.com/nagachaitanyaappana/Toolkit.git
cd Toolkit

# Install requirements
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Launch Toolkit on Windows
```powershell
# Launch Desktop GUI
python main.py

# Launch Terminal TUI
python main.py --cli
```

*(Tip: You can create a desktop shortcut pointing to `pythonw.exe main.py` to launch Toolkit without a background console window).*

---

### 🍎 macOS Setup

#### 1. Install Dependencies via Homebrew
```bash
# Install Homebrew if not already installed (https://brew.sh)
brew install python ffmpeg git
```

#### 2. Clone and Install
```bash
git clone https://github.com/nagachaitanyaappana/Toolkit.git
cd Toolkit

# Install requirements
pip3 install -r requirements.txt
```

#### 3. Launch Toolkit
```bash
# Launch Desktop GUI
python3 main.py

# Launch Terminal TUI
python3 main.py --cli
```

---

## 📁 Project Architecture

```
Toolkit/
├── main.py                     # Primary entry point (PyQt6 GUI default + CLI fallback)
├── toolkit                     # Linux executable bash runner
├── toolkit.desktop             # FreeDesktop application entry
├── pyproject.toml              # Build metadata & dependencies
├── requirements.txt            # Python package requirements
├── README.md                   # Documentation & setup manual
├── assets/
│   └── icon.png                # High-res Cyber Matrix application icon
├── core/
│   ├── engine.py               # Downloader extraction & validation engine
│   ├── formats.py              # Media stream data structures
│   └── options.py              # yt-dlp option builder & sanitizer
├── tools/
│   ├── downloader.py           # CLI downloader controller
│   ├── message_sender.py       # CLI email dispatcher & session storage
│   ├── password_mgr.py         # Encrypted Fernet vault & PBKDF2 derivation
│   ├── phone_checker.py        # Telecom lookup & Truecaller integration
│   ├── qr_generator.py         # ASCII / PNG QR generation
│   └── sysinfo.py              # Hardware monitoring & psutil metrics
└── ui/
    ├── gui/
    │   ├── main_window.py      # Master window, deck switcher & responsive handlers
    │   ├── theme.py            # Cyberpunk Emerald Matrix QSS stylesheets
    │   ├── components/
    │   │   ├── sidebar.py      # Collapsible responsive navigation bar
    │   │   ├── console_drawer.py # Real-time ANSI live output drawer
    │   │   └── toast.py        # Floating status feedback toasts
    │   └── views/
    │       ├── downloader_view.py # Progressive media downloader with live preview
    │       ├── password_view.py   # Encrypted vault & password generator
    │       ├── phone_view.py      # Phone validator & Truecaller intelligence
    │       ├── qr_view.py         # Interactive QR code studio
    │       ├── email_view.py      # Multi-message scheduler & email dispatcher
    │       └── sysinfo_view.py    # Real-time hardware telemetry gauges
    └── menus.py                # Terminal TUI menu system (Rich + Questionary)
```

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
