#!/usr/bin/env python3
"""
Toolkit — Cyber Matrix Control Center & Developer Toolkit.
Default native PyQt6 Desktop UI with fallback Rich TUI mode via --cli / --tui.
"""

from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))


def run_tui() -> None:
    """Run interactive terminal TUI menu loop."""
    from rich.console import Console
    from tools import get_all_tools
    from ui.menus import main_menu

    console = Console()
    tools = get_all_tools()

    while True:
        selected = main_menu(tools)
        if selected is None:
            console.print("\n[dim]👋  Thanks for using Toolkit! Goodbye![/dim]")
            break

        console.print(
            f"\n[bold cyan]▶  Running:[/bold cyan] {selected.icon} {selected.name}\n"
        )
        try:
            selected.run()
        except Exception as exc:
            console.print(f"[red]✗  Error: {exc}[/red]")
        else:
            console.print(f"\n[green]✓  Done with {selected.name}[/green]")

        try:
            import questionary

            again = questionary.confirm(
                "Return to main menu?",
                default=True,
            ).ask()
            if not again:
                console.print("\n[dim]👋  Thanks for using Toolkit! Goodbye![/dim]")
                break
        except (EOFError, KeyboardInterrupt):
            break


def main() -> None:
    if "-h" in sys.argv or "--help" in sys.argv:
        print("Toolkit — Cyber Matrix Control Center & Developer Toolkit")
        print("\nUsage:")
        print("  toolkit            Launch the native PyQt6 Desktop UI")
        print("  toolkit --cli      Launch the interactive terminal TUI menu")
        print("  toolkit --help     Show this help message")
        return

    # Check if CLI/TUI mode is explicitly requested
    if "--cli" in sys.argv or "--tui" in sys.argv or "-c" in sys.argv:
        run_tui()
        return

    # Check if display environment exists (X11 or Wayland)
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if not has_display:
        run_tui()
        return

    # Launch Native PyQt6 GUI
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QIcon
        from PyQt6.QtWidgets import QApplication

        from ui.gui.main_window import MainWindow
        from ui.gui.theme import CYBER_THEME_QSS

        # Allow terminal Ctrl+C
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # High DPI scaling
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        app = QApplication(sys.argv)
        app.setApplicationName("Toolkit")
        app.setApplicationDisplayName("Toolkit")
        app.setDesktopFileName("toolkit.desktop")

        icon_path = Path(__file__).resolve().parent / "assets" / "icon.png"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

        app.setStyleSheet(CYBER_THEME_QSS)

        window = MainWindow()
        window.show()

        sys.exit(app.exec())
    except Exception as exc:
        print(f"Failed to launch GUI ({exc}). Falling back to TUI...", file=sys.stderr)
        run_tui()


if __name__ == "__main__":
    main()
