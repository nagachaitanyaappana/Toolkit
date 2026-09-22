from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.console import Console

from tools import get_all_tools
from ui.menus import main_menu

console = Console()


def main() -> None:
    """Main toolkit loop: display menu, run selected tool, repeat."""
    tools = get_all_tools()

    while True:
        selected = main_menu(tools)
        if selected is None:
            console.print("\n[dim]👋  Thanks for using the Toolkit! Goodbye![/dim]")
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

        # Ask whether to return to menu or exit
        try:
            import questionary

            again = questionary.confirm(
                "Return to main menu?",
                default=True,
            ).ask()
            if not again:
                console.print("\n[dim]👋  Thanks for using the Toolkit! Goodbye![/dim]")
                break
        except (EOFError, KeyboardInterrupt):
            break


if __name__ == "__main__":
    main()
