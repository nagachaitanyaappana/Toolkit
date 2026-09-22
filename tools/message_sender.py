"""Tool: Gmail Message Sender — send emails with persistent login/logout sessions."""
from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

CONFIG_DIR = Path.home() / ".config" / "toolkit"
AUTH_FILE = CONFIG_DIR / "email_auth.json"

TEMPLATES = [
    {
        "name": "General Notification",
        "body": "Hello {name},\n\nThis is an automated notification from Toolkit.\nHope you are doing well!\n\nBest regards,\n{sender}",
    },
    {
        "name": "Verification Code",
        "body": "Dear {name},\n\nYour one-time verification code is: {code}\nThis code is valid for 10 minutes. Please do not share it with anyone.\n\nThanks,\n{sender}",
    },
    {
        "name": "Meeting / Task Reminder",
        "body": "Hi {name},\n\nQuick reminder: {meeting} is scheduled for {time}.\nPlease let me know if you need to reschedule.\n\nRegards,\n{sender}",
    },
    {
        "name": "Custom Follow-Up",
        "body": "Hello {name},\n\nFollowing up regarding our discussion on {topic}.\n{message}\n\nLooking forward to hearing from you,\n{sender}",
    },
]


def load_session() -> dict | None:
    """Load saved email credentials if available."""
    if not AUTH_FILE.exists():
        return None
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("email") and data.get("app_password"):
                return data
    except Exception:
        return None
    return None


def save_session(email: str, app_password: str) -> None:
    """Save email credentials with secure file permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    clean_password = app_password.replace(" ", "").strip()
    data = {
        "email": email.strip(),
        "app_password": clean_password,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "logged_in_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        os.chmod(AUTH_FILE, 0o600)
    except Exception:
        pass


def delete_session() -> None:
    """Delete saved session credentials on logout."""
    if AUTH_FILE.exists():
        try:
            AUTH_FILE.unlink()
        except Exception:
            pass


def test_smtp_connection(email: str, app_password: str) -> tuple[bool, str]:
    """Test connection and credentials against Gmail's SMTP server."""
    clean_password = app_password.replace(" ", "").strip()
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.starttls()
        server.login(email.strip(), clean_password)
        server.quit()
        return True, "Authentication successful!"
    except smtplib.SMTPAuthenticationError:
        return (
            False,
            "Authentication failed. Please verify your Gmail address and 16-character App Password.",
        )
    except Exception as exc:
        return False, f"Connection error: {exc}"


class MessageSenderTool:
    """Send emails via Gmail with persistent login sessions and templates."""

    name: str = "Gmail Message Sender"
    description: str = "Send emails with Gmail login/logout session and templates."
    icon: str = "✉️"

    def run(self) -> None:
        while True:
            session = load_session()
            console.clear() if hasattr(console, "clear") else None

            # Header Panel
            if session:
                status_text = f"[bold green]● Logged In:[/bold green] [cyan]{session['email']}[/cyan]"
            else:
                status_text = "[bold yellow]○ Not Logged In[/bold yellow] [dim](Login required to send emails)[/dim]"

            console.print(
                Panel(
                    Text("✉️   Gmail Message Sender", style="bold cyan"),
                    subtitle=status_text,
                    expand=False,
                )
            )

            if session:
                choices = [
                    {"name": "📨  Send an Email", "value": "send"},
                    {"name": "🔍  Verify Connection / Account Info", "value": "info"},
                    {"name": "🚪  Logout", "value": "logout"},
                    {"name": "↩   Return to Main Menu", "value": "exit"},
                ]
            else:
                choices = [
                    {"name": "🔑  Login with Gmail", "value": "login"},
                    {"name": "ℹ️   How to get a Google App Password", "value": "help"},
                    {"name": "↩   Return to Main Menu", "value": "exit"},
                ]

            action = questionary.select("Choose an option:", choices=choices).ask()
            if action in ("exit", None):
                return

            if action == "login":
                self._login_flow()
            elif action == "logout":
                self._logout_flow()
            elif action == "help":
                self._show_help()
            elif action == "info":
                self._show_account_info(session)
            elif action == "send":
                self._send_email_flow(session)

    def _login_flow(self) -> None:
        console.print("\n[bold cyan]🔑  Gmail Login[/bold cyan]")
        console.print(
            "[dim]Note: Gmail requires a 16-character 'App Password', not your regular password.[/dim]\n"
        )

        email = questionary.text(
            "Enter your Gmail address:",
            validate=lambda x: "@" in x and "." in x,
        ).ask()
        if not email:
            return

        password = questionary.password(
            "Enter your 16-character Google App Password:",
            validate=lambda x: len(x.replace(" ", "").strip()) >= 8,
        ).ask()
        if not password:
            return

        console.print("\n⏳ [cyan]Verifying credentials with smtp.gmail.com...[/cyan]")
        success, msg = test_smtp_connection(email, password)
        if success:
            save_session(email, password)
            console.print(f"\n[green]✓ {msg}[/green]")
            console.print(f"[bold green]✓ Logged in as: {email}[/bold green]")
        else:
            console.print(f"\n[red]✗ {msg}[/red]")
            console.print(
                "[yellow]Tip: Go to myaccount.google.com/apppasswords to create a 16-character App Password.[/yellow]"
            )

        input("\n[Enter] to continue...")

    def _logout_flow(self) -> None:
        confirm = questionary.confirm(
            "Are you sure you want to log out and clear saved credentials?",
            default=False,
        ).ask()
        if confirm:
            delete_session()
            console.print("\n[green]✓ Successfully logged out.[/green]")
            input("\n[Enter] to continue...")

    def _show_help(self) -> None:
        console.print("\n[bold cyan]ℹ️   How to get a Google App Password (2 Minutes):[/bold cyan]\n")
        steps = [
            "1. Open your browser and go to: [bold underline]https://myaccount.google.com/security[/bold underline]",
            "2. Make sure [bold cyan]2-Step Verification[/bold cyan] is turned ON.",
            "3. Search for '[bold cyan]App passwords[/bold cyan]' in the search bar (or visit: https://myaccount.google.com/apppasswords).",
            "4. Under 'App name', enter '[bold green]Toolkit[/bold green]' and click [bold]Create[/bold].",
            "5. Google will generate a 16-character password (e.g. `abcd efgh ijkl mnop`).",
            "6. Copy that 16-character code and paste it into the Toolkit login prompt.",
        ]
        for step in steps:
            console.print(f"  {step}")
        console.print(
            "\n[dim]Why? Google disabled simple password logins for security. App Passwords ensure your main password stays safe.[/dim]"
        )
        input("\n[Enter] to return...")

    def _show_account_info(self, session: dict) -> None:
        console.print("\n[bold cyan]📋  Active Gmail Account[/bold cyan]")
        table = Table(show_header=False, border_style="cyan")
        table.add_column("Key", style="dim")
        table.add_column("Value", style="bold")
        table.add_row("Email", session["email"])
        table.add_row("SMTP Server", f"{session['smtp_server']}:{session['smtp_port']}")
        table.add_row("Logged in since", session.get("logged_in_at", "Unknown"))
        console.print(table)

        console.print("\n⏳ [cyan]Testing connection to smtp.gmail.com...[/cyan]")
        success, msg = test_smtp_connection(session["email"], session["app_password"])
        if success:
            console.print("[green]✓ Connection active & working![/green]")
        else:
            console.print(f"[red]✗ Connection failed: {msg}[/red]")
        input("\n[Enter] to continue...")

    def _send_email_flow(self, session: dict) -> None:
        from_email = session["email"]
        password = session["app_password"]

        to_email = questionary.text(
            "To Email address:",
            validate=lambda x: "@" in x and "." in x,
        ).ask()
        if not to_email:
            return

        subject = questionary.text(
            "Subject:",
            validate=lambda x: bool(x.strip()),
        ).ask()
        if not subject:
            return

        # Message body type
        mode = questionary.select(
            "Message Body:",
            choices=[
                {"name": "📋  Use a Template", "value": "template"},
                {"name": "✍️   Write Quick Message (Single Line)", "value": "quick"},
                {"name": "📝  Write Multi-line Message", "value": "multi"},
            ],
        ).ask()
        if not mode:
            return

        message_body = ""
        if mode == "template":
            tmpl_choices = [
                {"name": f"{t['name']}", "value": idx}
                for idx, t in enumerate(TEMPLATES)
            ]
            selected_idx = questionary.select("Select template:", choices=tmpl_choices).ask()
            if selected_idx is None:
                return
            template = TEMPLATES[selected_idx]["body"]
            message_body = self._fill_template(template, from_email)
        elif mode == "quick":
            message_body = questionary.text("Enter message:").ask()
            if not message_body:
                return
        elif mode == "multi":
            console.print("\n[yellow]Type your message below. Enter an empty line when done:[/yellow]\n")
            lines = []
            while True:
                try:
                    line = input("  > ")
                    if not line:
                        if lines:
                            break
                        else:
                            console.print("[dim](Press Enter again to finish, or type your message)[/dim]")
                            continue
                    lines.append(line)
                except (EOFError, KeyboardInterrupt):
                    break
            message_body = "\n".join(lines).strip()
            if not message_body:
                console.print("[yellow]No message entered. Aborting.[/yellow]")
                input("\n[Enter] to continue...")
                return

        # Preview Panel
        console.print()
        preview_text = (
            f"[bold cyan]From:[/bold cyan]    {from_email}\n"
            f"[bold cyan]To:[/bold cyan]      {to_email}\n"
            f"[bold cyan]Subject:[/bold cyan] {subject}\n\n"
            f"[dim]─── Message Body ───[/dim]\n"
            f"{message_body}"
        )
        console.print(Panel(Text.from_markup(preview_text), title=" Email Preview ", expand=False))

        confirm = questionary.confirm("Send this email now?", default=True).ask()
        if not confirm:
            console.print("[yellow]↩ Cancelled. Email was not sent.[/yellow]")
            input("\n[Enter] to continue...")
            return

        console.print("\n⏳ [cyan]Sending email...[/cyan]")
        try:
            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(message_body, "plain"))

            server = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
            server.quit()

            console.print(f"\n[bold green]✓  Email successfully sent to {to_email}![/bold green]")
        except smtplib.SMTPAuthenticationError:
            console.print("\n[red]✗  SMTP authentication failed. Your App Password may have expired.[/red]")
        except smtplib.SMTPRecipientsRefused:
            console.print(f"\n[red]✗  Recipient address rejected: {to_email}[/red]")
        except Exception as exc:
            console.print(f"\n[red]✗  Failed to send: {exc}[/red]")

        input("\n[Enter] to return to menu...")

    def _fill_template(self, template: str, sender_email: str) -> str:
        import re

        placeholders = sorted(set(re.findall(r"\{(\w+)\}", template)))
        result = template
        sender_name = sender_email.split("@")[0].replace(".", " ").title()

        console.print("\n[dim]Fill in template values:[/dim]")
        for ph in placeholders:
            default_val = sender_name if ph == "sender" else ""
            val = questionary.text(
                f"Value for '{ph}':",
                default=default_val,
            ).ask()
            result = result.replace(f"{{{ph}}}", val or f"[{ph}]")

        return result
