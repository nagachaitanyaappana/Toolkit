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


def main_menu(tools: list) -> object | None:
    """
    Display the main menu using letter-key navigation.

    a) Tool 1
    b) Tool 2
    ...
    x) Exit

    Returns the selected tool instance, or ``None`` to exit.
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    console = Console()

    # Print header banner
    console.print(
        Panel(
            Text("🎯  THE TOOLKIT  🎯", style="bold cyan"),
            title="v1.0",
            border_style="cyan",
            expand=False,
        )
    )

    # List tools with letter keys
    letters = "abcdefghijklmnopqrstuvwxyz"
    for idx, tool in enumerate(tools):
        letter = letters[idx] if idx < len(letters) else str(idx)
        line = f"[bold]{letter})[/bold]  {tool.icon}  {tool.name}"
        console.print(f"  {line}")

    console.print()
    console.print("  x)  ❌  Exit")
    console.print()
    console.print("[dim]Type a letter to select a tool, or 'x' to exit.[/dim]")

    # Letter-key input loop
    while True:
        try:
            raw = input("🔍 Select: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None

        if raw in ("x", "q", "quit", "exit", ""):
            return None

        if len(raw) == 1 and raw.isalpha():
            idx = letters.index(raw)
            if idx < len(tools):
                return tools[idx]

        console.print("[red]✗  Invalid selection. Please type a letter.[/red]")
