"""Tool: Password Manager — encrypted credentials vault with password generator and clipboard support."""
from __future__ import annotations

import base64
import json
import os
import random
import secrets
import string
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

CONFIG_DIR = Path.home() / ".config" / "toolkit"
VAULT_FILE = CONFIG_DIR / "vault.enc"


def derive_key(master_password: str, salt: bytes) -> bytes:
    """Derive an AES-Fernet encryption key from the master password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))


def generate_random_password(
    length: int = 16,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """Generate a cryptographically secure random password."""
    pools = []
    required = []

    if use_upper:
        pools.append(string.ascii_uppercase)
        required.append(secrets.choice(string.ascii_uppercase))
    if use_lower:
        pools.append(string.ascii_lowercase)
        required.append(secrets.choice(string.ascii_lowercase))
    if use_digits:
        pools.append(string.digits)
        required.append(secrets.choice(string.digits))
    if use_symbols:
        syms = "!@#$%^&*()-_=+[]{}|;:,.<>?"
        pools.append(syms)
        required.append(secrets.choice(syms))

    if not pools:
        pools.append(string.ascii_letters + string.digits)
        required.append(secrets.choice(string.ascii_letters))

    all_chars = "".join(pools)
    remaining_len = max(0, length - len(required))
    chars = required + [secrets.choice(all_chars) for _ in range(remaining_len)]
    random.shuffle(chars)
    return "".join(chars)


class PasswordManagerTool:
    """Secure encrypted password vault with password generation and clipboard copy."""

    name: str = "Password Manager"
    description: str = "Encrypted password vault with generator & clipboard copy."
    icon: str = "🔐"

    def run(self) -> None:
        console.print(
            Panel(Text("🔐  Password Manager & Vault", style="bold cyan"), expand=False)
        )

        master_pw, vault_data = self._unlock_or_setup_vault()
        if master_pw is None or vault_data is None:
            return

        while True:
            console.print()
            choices = [
                {"name": f"📋  View / Copy Accounts ({len(vault_data)} saved)", "value": "list"},
                {"name": "➕  Add New Account / Password", "value": "add"},
                {"name": "🎲  Generate a Strong Password", "value": "gen"},
                {"name": "🔄  Change Master Password", "value": "change_master"},
                {"name": "🔒  Lock Vault & Return to Main Menu", "value": "exit"},
            ]

            action = questionary.select("Choose an option:", choices=choices).ask()
            if action in ("exit", None):
                console.print("\n[dim]🔒 Vault locked.[/dim]")
                return

            if action == "list":
                self._view_accounts_flow(master_pw, vault_data)
            elif action == "add":
                self._add_account_flow(master_pw, vault_data)
            elif action == "gen":
                self._generate_flow(master_pw, vault_data)
            elif action == "change_master":
                new_pw = self._change_master_flow(master_pw, vault_data)
                if new_pw:
                    master_pw = new_pw

    def _unlock_or_setup_vault(self) -> tuple[str | None, list[dict] | None]:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        if not VAULT_FILE.exists():
            console.print("\n[bold yellow]Welcome to your new Password Vault![/bold yellow]")
            console.print("[dim]Set a Master Password. All credentials will be encrypted with AES-256.[/dim]\n")

            while True:
                pw1 = questionary.password("Create Master Password:").ask()
                if not pw1 or len(pw1) < 4:
                    console.print("[red]Master password must be at least 4 characters.[/red]")
                    return None, None

                pw2 = questionary.password("Confirm Master Password:").ask()
                if pw1 != pw2:
                    console.print("[red]Passwords do not match. Try again.[/red]\n")
                    continue

                salt = os.urandom(16)
                empty_vault: list[dict] = []
                self._save_vault(pw1, salt, empty_vault)
                console.print("\n[green]✓ Master Password set and vault initialized![/green]")
                return pw1, empty_vault

        # Vault exists — unlock
        for _ in range(3):
            master_pw = questionary.password("Enter Master Password to unlock vault (or leave blank to return):").ask()
            if not master_pw:
                return None, None

            data = self._read_vault(master_pw)
            if data is not None:
                console.print("[green]✓ Vault unlocked![/green]")
                return master_pw, data

            console.print("[red]✗ Incorrect Master Password. Try again.[/red]\n")

        console.print("[red]Too many failed attempts. Returning to main menu.[/red]")
        return None, None

    def _read_vault(self, master_password: str) -> list[dict] | None:
        try:
            with open(VAULT_FILE, "rb") as f:
                content = f.read()

            salt = content[:16]
            encrypted = content[16:]

            key = derive_key(master_password, salt)
            fernet = Fernet(key)
            decrypted = fernet.decrypt(encrypted)
            return json.loads(decrypted.decode("utf-8"))
        except (InvalidToken, Exception):
            return None

    def _save_vault(self, master_password: str, salt: bytes | None, data: list[dict]) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if salt is None:
            if VAULT_FILE.exists():
                with open(VAULT_FILE, "rb") as f:
                    salt = f.read(16)
            else:
                salt = os.urandom(16)

        key = derive_key(master_password, salt)
        fernet = Fernet(key)
        payload = json.dumps(data, indent=2).encode("utf-8")
        encrypted = fernet.encrypt(payload)

        with open(VAULT_FILE, "wb") as f:
            f.write(salt + encrypted)

        try:
            os.chmod(VAULT_FILE, 0o600)
        except Exception:
            pass

    def _view_accounts_flow(self, master_pw: str, vault_data: list[dict]) -> None:
        if not vault_data:
            console.print("\n[yellow]No accounts saved yet. Choose 'Add New Account' to store one.[/yellow]")
            return

        # Sort accounts by service name
        vault_data.sort(key=lambda x: x.get("service", "").lower())

        table = Table(title=" Saved Accounts in Vault ", show_header=True, border_style="cyan")
        table.add_column("#", style="dim", justify="right")
        table.add_column("Service / App", style="bold cyan")
        table.add_column("Username / Email")
        table.add_column("Password")
        table.add_column("Notes", style="dim")

        for idx, acc in enumerate(vault_data, 1):
            table.add_row(
                str(idx),
                acc.get("service", "Unknown"),
                acc.get("username", "-"),
                "••••••••••••",
                acc.get("notes", "-") or "-",
            )

        console.print()
        console.print(table)

        choices = [
            {
                "name": f"{idx}. {acc.get('service')} ({acc.get('username')})",
                "value": idx - 1,
            }
            for idx, acc in enumerate(vault_data, 1)
        ]
        choices.append({"name": "↩  Back", "value": None})

        selected_idx = questionary.select("Select an account to manage:", choices=choices).ask()
        if selected_idx is None:
            return

        acc = vault_data[selected_idx]
        self._manage_single_account(master_pw, vault_data, selected_idx)

    def _manage_single_account(self, master_pw: str, vault_data: list[dict], idx: int) -> None:
        acc = vault_data[idx]

        sub_choices = [
            {"name": "📋  Copy Password to Clipboard", "value": "copy"},
            {"name": "👁️   Reveal Password", "value": "reveal"},
            {"name": "✏️   Edit Account", "value": "edit"},
            {"name": "🗑️   Delete Account", "value": "delete"},
            {"name": "↩   Back", "value": "back"},
        ]

        action = questionary.select(f"Manage '{acc.get('service')}':", choices=sub_choices).ask()

        if action == "copy":
            try:
                import pyperclip
                pyperclip.copy(acc.get("password", ""))
                console.print(f"\n[bold green]✓ Password for {acc.get('service')} copied to clipboard![/bold green]")
            except Exception:
                console.print(f"\n[yellow]Password: {acc.get('password')}[/yellow]")
            input("\n[Enter] to continue...")

        elif action == "reveal":
            console.print()
            panel_text = (
                f"[bold cyan]Service:[/bold cyan]  {acc.get('service')}\n"
                f"[bold cyan]Username:[/bold cyan] {acc.get('username')}\n"
                f"[bold cyan]Password:[/bold cyan] [bold green]{acc.get('password')}[/bold green]\n"
                f"[bold cyan]Notes:[/bold cyan]    {acc.get('notes') or '-'}"
            )
            console.print(Panel(Text.from_markup(panel_text), title=" Account Details ", expand=False))
            input("\n[Enter] to continue...")

        elif action == "edit":
            service = questionary.text("Service / Website:", default=acc.get("service", "")).ask()
            username = questionary.text("Username / Email:", default=acc.get("username", "")).ask()
            pw = questionary.text("Password:", default=acc.get("password", "")).ask()
            notes = questionary.text("Notes:", default=acc.get("notes", "")).ask()

            if service and pw:
                acc["service"] = service.strip()
                acc["username"] = username.strip()
                acc["password"] = pw.strip()
                acc["notes"] = notes.strip()
                self._save_vault(master_pw, None, vault_data)
                console.print("\n[green]✓ Account updated![/green]")

        elif action == "delete":
            confirm = questionary.confirm(f"Permanently delete '{acc.get('service')}'?", default=False).ask()
            if confirm:
                vault_data.pop(idx)
                self._save_vault(master_pw, None, vault_data)
                console.print("\n[green]✓ Account deleted from vault.[/green]")

    def _add_account_flow(self, master_pw: str, vault_data: list[dict]) -> None:
        console.print("\n[bold cyan]➕  Add New Account[/bold cyan]")
        service = questionary.text("Service or Website (e.g. GitHub, Netflix):").ask()
        if not service:
            return

        username = questionary.text("Username or Email:").ask()

        pw_method = questionary.select(
            "Password:",
            choices=[
                {"name": "🎲  Generate strong random password", "value": "gen"},
                {"name": "✍️   Type password manually", "value": "manual"},
            ],
        ).ask()

        if pw_method == "gen":
            pw = generate_random_password(length=18)
            console.print(f"\nGenerated password: [bold green]{pw}[/bold green]")
        else:
            pw = questionary.password("Enter Password:").ask()
            if not pw:
                return

        notes = questionary.text("Notes (optional):").ask()

        vault_data.append({
            "service": service.strip(),
            "username": (username or "").strip(),
            "password": pw.strip(),
            "notes": (notes or "").strip(),
        })

        self._save_vault(master_pw, None, vault_data)
        console.print(f"\n[bold green]✓ Successfully saved '{service}' to your vault![/bold green]")

        try:
            import pyperclip
            pyperclip.copy(pw.strip())
            console.print("[dim](Password copied to clipboard)[/dim]")
        except Exception:
            pass

        input("\n[Enter] to continue...")

    def _generate_flow(self, master_pw: str, vault_data: list[dict]) -> None:
        console.print("\n[bold cyan]🎲  Password Generator[/bold cyan]")
        len_str = questionary.text("Password length (8-64, default 16):", default="16").ask()
        try:
            length = max(8, min(64, int(len_str)))
        except ValueError:
            length = 16

        symbols = questionary.confirm("Include symbols (!@#$%^&*)?", default=True).ask()
        digits = questionary.confirm("Include numbers (0-9)?", default=True).ask()

        pw = generate_random_password(length=length, use_symbols=symbols, use_digits=digits)

        console.print()
        console.print(
            Panel(
                Text(pw, style="bold green"),
                title=f" Generated Password ({length} chars) ",
                border_style="green",
                expand=False,
            )
        )

        action = questionary.select(
            "What would you like to do?",
            choices=[
                {"name": "📋  Copy to Clipboard", "value": "copy"},
                {"name": "💾  Save directly to Vault", "value": "save"},
                {"name": "↩   Done", "value": "done"},
            ],
        ).ask()

        if action == "copy":
            try:
                import pyperclip
                pyperclip.copy(pw)
                console.print("[green]✓ Copied to clipboard![/green]")
            except Exception:
                console.print("[yellow]pyperclip not available.[/yellow]")
            input("\n[Enter] to continue...")

        elif action == "save":
            service = questionary.text("Service Name:").ask()
            username = questionary.text("Username / Email:").ask()
            if service:
                vault_data.append({
                    "service": service.strip(),
                    "username": (username or "").strip(),
                    "password": pw,
                    "notes": "",
                })
                self._save_vault(master_pw, None, vault_data)
                console.print(f"[green]✓ Saved to vault under '{service}'![/green]")
                input("\n[Enter] to continue...")

    def _change_master_flow(self, current_pw: str, vault_data: list[dict]) -> str | None:
        verify = questionary.password("Enter current Master Password:").ask()
        if verify != current_pw:
            console.print("[red]✗ Incorrect Master Password.[/red]")
            input("\n[Enter] to continue...")
            return None

        new1 = questionary.password("Enter New Master Password:").ask()
        if not new1 or len(new1) < 4:
            console.print("[red]Password too short.[/red]")
            return None

        new2 = questionary.password("Confirm New Master Password:").ask()
        if new1 != new2:
            console.print("[red]Passwords do not match.[/red]")
            return None

        new_salt = os.urandom(16)
        self._save_vault(new1, new_salt, vault_data)
        console.print("\n[bold green]✓ Master Password updated successfully![/bold green]")
        input("\n[Enter] to continue...")
        return new1
