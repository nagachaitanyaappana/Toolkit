"""Tool: Password Generator — generate secure random passwords."""
from __future__ import annotations

import random
import string

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


class PasswordGeneratorTool:
    """Generate secure, random passwords with customizable options."""

    name: str = "Password Generator"
    description: str = "Generate secure, random passwords."
    icon: str = "🔐"

    def run(self) -> None:
        console.print(
            Panel(Text("🔐  Password Generator", style="bold cyan"), expand=False)
        )

        while True:
            self._generate()

            again = input("\n  Generate another password? (y/n): ").strip().lower()
            if again != "y":
                return

    def _generate(self) -> None:
        # Get password length
        length_str = input("\n📏 Password length (8-128, default 16): ").strip()
        if not length_str:
            length = 16
        elif length_str.isdigit() and 8 <= int(length_str) <= 128:
            length = int(length_str)
        else:
            console.print("[red]✗  Invalid length. Using default 16.[/red]")
            length = 16

        # Ask about character sets
        console.print("\n[dim]Select character sets to include:[/dim]")
        use_upper = input("  Include uppercase letters? (Y/n): ").strip().lower() != "n"
        use_lower = input("  Include lowercase letters? (Y/n): ").strip().lower() != "n"
        use_digits = input("  Include digits? (Y/n): ").strip().lower() != "n"
        use_symbols = input("  Include symbols? (Y/n): ").strip().lower() != "n"

        if not any([use_upper, use_lower, use_digits, use_symbols]):
            console.print("[red]✗  Must include at least one character set![/red]")
            use_lower = True

        # Build character pool
        pool = ""
        if use_upper:
            pool += string.ascii_uppercase
        if use_lower:
            pool += string.ascii_lowercase
        if use_digits:
            pool += string.digits
        if use_symbols:
            pool += "!@#$%^&*()-_=+[]{}|;:,.<>?"

        # Generate password ensuring at least one char from each selected set
        password_chars = []
        if use_upper:
            password_chars.append(random.choice(string.ascii_uppercase))
        if use_lower:
            password_chars.append(random.choice(string.ascii_lowercase))
        if use_digits:
            password_chars.append(random.choice(string.digits))
        if use_symbols:
            password_chars.append(random.choice("!@#$%^&*()-_=+[]{}|;:,.<>?"))

        for _ in range(length - len(password_chars)):
            password_chars.append(random.choice(pool))

        random.shuffle(password_chars)
        password = "".join(password_chars)

        # Display result
        console.print()
        console.print(Panel(
            Text(password, style="bold green"),
            title=f" 🔐 Generated Password ({length} chars) ",
            border_style="green",
        ))

        # Show character set breakdown
        breakdown = []
        if use_upper:
            breakdown.append("A-Z")
        if use_lower:
            breakdown.append("a-z")
        if use_digits:
            breakdown.append("0-9")
        if use_symbols:
            breakdown.append("symbols")
        console.print(f"[dim]Charsets: {', '.join(breakdown)}[/dim]")

        # Copy to clipboard option
        copy = input("\n  Copy to clipboard? (y/n): ").strip().lower()
        if copy == "y":
            try:
                import pyperclip
                pyperclip.copy(password)
                console.print("[green]✓  Copied to clipboard![/green]")
            except ImportError:
                console.print("[yellow]!  pyperclip not installed. Password shown above.[/yellow]")
                console.print(f"[cyan]Password: {password}[/cyan]")