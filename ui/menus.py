from __future__ import annotations

from typing import Sequence

import questionary


def select_platform() -> str:
    return questionary.select(
        "Platform:",
        choices=[
            "YouTube",
            "Instagram",
            "Reddit",
            "TikTok",
            "X / Twitter",
            "Other / yt-dlp supported site",
        ],
    ).ask()


def prompt_url(platform: str) -> str:
    return questionary.text(
        "Video URL:",
        validate=lambda x: bool(x.strip()),
    ).ask()


def select_download_type() -> str:
    return questionary.select(
        "Download type:",
        choices=[
            "Video",
            "Audio",
        ],
    ).ask()


def select_video_quality(formats: list[dict]) -> str:
    choices = [
        {
            "name": f"{fmt.get('resolution', 'unknown')} ({fmt.get('ext', '')}) - {fmt.get('format_note', '') or 'no note'}",
            "value": fmt.get("format_id", ""),
        }
        for fmt in formats
    ]
    return questionary.select("Quality:", choices=choices).ask()


def select_audio_format() -> str:
    return questionary.select(
        "Audio format:",
        choices=[
            {"name": "MP3", "value": "mp3"},
            {"name": "M4A", "value": "m4a"},
            {"name": "WAV", "value": "wav"},
            {"name": "FLAC", "value": "flac"},
        ],
    ).ask()


def select_video_format() -> str:
    return questionary.select(
        "Format:",
        choices=[
            {"name": "MP4", "value": "mp4"},
            {"name": "MKV", "value": "mkv"},
            {"name": "WebM", "value": "webm"},
        ],
    ).ask()


def confirm_download(title: str) -> bool:
    return questionary.confirm(
        f"Download \"{title}\"?",
        default=True,
    ).ask()


def wait_for_enter(message: str = "Press Enter to continue...") -> None:
    questionary.print(message)
    input()
