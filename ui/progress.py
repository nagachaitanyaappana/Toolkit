from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def show_banner() -> None:
    console = Console()
    console.print(
        Panel(
            Text("🎬 Universal Downloader", style="bold magenta"),
            expand=False,
        )
    )


def show_error(message: str) -> None:
    console = Console()
    console.print(f"[red]Error:[/red] {message}")


def show_success(message: str) -> None:
    console = Console()
    console.print(f"[green]✓ {message}[/green]")


def format_speed(speed: float | None) -> str:
    if not speed:
        return "-- MB/s"
    return f"{speed / 1024 / 1024:.2f} MB/s"


def format_eta(eta: float | None) -> str:
    if not eta:
        return "--:--"
    minutes = int(eta // 60)
    seconds = int(eta % 60)
    return f"{minutes:02d}:{seconds:02d}"
