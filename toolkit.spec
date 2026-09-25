# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# Platform-specific icon
if sys.platform == "win32":
    icon_file = os.path.join("assets", "icon.ico")
else:
    icon_file = os.path.join("assets", "icon.png")

datas = [
    ('assets', 'assets'),
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'cryptography',
        'yt_dlp',
        'rich',
        'questionary',
        'phonenumbers',
        'qrcode',
        'psutil',
        'requests',
        'pyperclip',
        'PIL',
        'tools',
        'tools.downloader',
        'tools.message_sender',
        'tools.phone_checker',
        'tools.qr_generator',
        'tools.password_mgr',
        'tools.sysinfo',
        'ui',
        'ui.gui',
        'ui.gui.main_window',
        'ui.gui.theme',
        'ui.menus',
        'core',
        'utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Toolkit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file if os.path.exists(icon_file) else None,
)
