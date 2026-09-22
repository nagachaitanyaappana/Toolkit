from __future__ import annotations

from typing import Sequence

import questionary


def select_platform() -> str:
    return questionary.select(
        "Platform:",
        choices=[
            "YouTube",
            "Instagram",
            "Spotify",
            "Pinterest",
            "X / Twitter",
            "Reddit",
            "Other / Universal (Any supported site)",
        ],
    ).ask()


def prompt_url(platform: str) -> str:
    return questionary.text(
        "URL:",
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


def select_resolution() -> str | None:
    return questionary.select(
        "Select Video Quality:",
        choices=[
            {"name": "🌟  Best Available (Original / 4K / 2K / 1080p)", "value": "best"},
            {"name": "📺  1080p Full HD", "value": "1080"},
            {"name": "📱  720p HD (Balanced size & speed)", "value": "720"},
            {"name": "⚡  480p Data Saver (Small file)", "value": "480"},
        ],
    ).ask()


def select_playlist_mode() -> str | None:
    return questionary.select(
        "This link contains both a single video and a playlist. What would you like to download?",
        choices=[
            {"name": "▶   Download this single video only (Recommended)", "value": "single"},
            {"name": "📑  Download the entire playlist", "value": "playlist"},
        ],
    ).ask()


def select_browser_cookies() -> str | None:
    return questionary.select(
        "This content may require login or cookies. Use cookies from an installed browser?",
        choices=[
            {"name": "🌐  Chrome", "value": "chrome"},
            {"name": "🦊  Firefox", "value": "firefox"},
            {"name": "🦁  Brave", "value": "brave"},
            {"name": "🌊  Edge", "value": "edge"},
            {"name": "❌  None (Skip)", "value": "none"},
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
            {"name": "🎵  MP3 (High Quality 320kbps)", "value": "mp3"},
            {"name": "🎧  M4A (AAC)", "value": "m4a"},
            {"name": "🎼  FLAC (Lossless)", "value": "flac"},
            {"name": "📻  WAV (Uncompressed)", "value": "wav"},
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


def main_menu(tools: list) -> object | None:
    """
    Display the main menu using smooth arrow-key navigation.
    Supports Up/Down arrows, j/k Vim keys, number shortcuts (1-9), and Enter to select.
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    console = Console()

    console.print()
    console.print(
        Panel(
            Text("🎯   T H E   T O O L K I T   🎯", style="bold cyan"),
            title="[bold cyan]v1.0.0[/bold cyan]",
            subtitle="[dim]Use ↑/↓ arrows (or 1-8 keys) to navigate, Enter to launch[/dim]",
            border_style="cyan",
            expand=False,
        )
    )

    choices = [
        {
            "name": f"{tool.icon}  {tool.name:<24} ── {tool.description}",
            "value": tool,
        }
        for tool in tools
    ]
    choices.append(questionary.Separator("─" * 60))
    choices.append({"name": "❌  Exit Toolkit", "value": None})

    try:
        selected = questionary.select(
            "Choose a tool to launch:",
            choices=choices,
            use_shortcuts=True,
            use_arrow_keys=True,
            use_jk_keys=True,
            use_indicator=True,
        ).ask()
        return selected
    except (KeyboardInterrupt, EOFError):
        return None
