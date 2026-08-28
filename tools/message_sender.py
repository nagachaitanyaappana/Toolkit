"""Tool: Auto Message Sender — send messages via email or Discord with templates."""
from __future__ import annotations

import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# Simple template system
TEMPLATES = [
    "Hello {name},\n\nThis is an automated message from the Toolkit.\nHope you're doing well!",
    "Dear {name},\n\nYour verification code is: {code}\nPlease enter this code to continue.",
    "Hi {name},\n\nMeeting reminder: {meeting} at {time}.\nDon't forget!",
    "Hello {name},\n\n{message}\n\nThanks!",
]


class MessageSenderTool:
    """Send messages via email or Discord webhooks with templates."""

    name: str = "Auto Message Sender"
    description: str = "Send messages via email or Discord with templates."
    icon: str = "✉️"

    def run(self) -> None:
        console.print(
            Panel(Text("✉️  Auto Message Sender", style="bold cyan"), expand=False)
        )

        while True:
            console.print("\n[dim]Select channel:[/dim]")
            console.print("  1) Email (SMTP)")
            console.print("  2) Discord Webhook")
            console.print("  x) Return to menu")

            choice = input("\n▶  Select: ").strip().lower()

            if choice == "1":
                self._send_email()
            elif choice == "2":
                self._send_discord()
            elif choice in ("x", "q", ""):
                return
            else:
                console.print("[red]✗  Invalid choice.[/red]")

    def _select_template(self) -> str:
        while True:
            console.print("\n[dim]Templates:[/dim]")
            for i, tmpl in enumerate(TEMPLATES, 1):
                preview = tmpl.replace("{name}", "***").replace("{code}", "***").replace("{meeting}", "***").replace("{time}", "***").replace("{message}", "***")
                console.print(f"  {i}) {preview[:60]}...")
            console.print("  0) Write custom message")

            try:
                choice = int(input("\n▶  Select template (0-{max}): ".format(max=len(TEMPLATES))))
            except ValueError:
                console.print("[red]✗  Invalid number.[/red]")
                continue

            if choice == 0:
                console.print("\n[yellow]Enter your message (single line, press Enter when done):[/yellow]")
                custom = input(">  ")
                if not custom:
                    console.print("[yellow]↩  No message entered.[/yellow]")
                    return ""
                return custom
            elif 1 <= choice <= len(TEMPLATES):
                return TEMPLATES[choice - 1]
            else:
                console.print("[red]✗  Out of range.[/red]")

    def _fill_template(self, template: str) -> str:
        placeholders = set()
        temp = template
        # Find all {placeholder} patterns
        import re
        for match in re.finditer(r"\{(\w+)\}", template):
            placeholders.add(match.group(1))

        for ph in sorted(placeholders):
            value = input(f"\n  Fill in '{ph}': ").strip()
            temp = temp.replace(f"{{{ph}}}", value if value else f"{{{ph}}}")

        return temp

    def _send_email(self) -> None:
        console.print()
        from_email = input("📤 From email: ").strip()
        password = input("  Password (app password for Gmail): ").strip()
        smtp_server = input("  SMTP server (e.g., smtp.gmail.com): ").strip()
        smtp_port_str = input("  SMTP port (default 587): ").strip()
        try:
            smtp_port = int(smtp_port_str) if smtp_port_str else 587
        except ValueError:
            smtp_port = 587

        to_email = input("\n📨 To email: ").strip()
        subject = input("  Subject: ").strip()

        template = self._select_template()
        if not template:
            return

        message = self._fill_template(template)

        console.print()
        console.print(Panel(Text(message, style="dim"), title=" Preview ", expand=False))

        confirm = input("\n  Send? (y/n): ").strip().lower()
        if confirm != "y":
            console.print("[yellow]↩  Not sent.[/yellow]")
            return

        try:
            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(message, "plain"))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
            server.quit()

            console.print("[green]✓  Email sent successfully![/green]")
        except smtplib.SMTPAuthenticationError:
            console.print("[red]✗  SMTP authentication failed. Check credentials.[/red]")
        except smtplib.SMTPRecipientsRefused:
            console.print("[red]✗  Recipient email rejected.[/red]")
        except Exception as exc:
            console.print(f"[red]✗  Failed to send: {exc}[/red]")

    def _send_discord(self) -> None:
        webhook_url = input("\n🔗 Discord webhook URL: ").strip()
        if not webhook_url:
            console.print("[yellow]↩  No URL entered.[/yellow]")
            return

        template = self._select_template()
        if not template:
            return

        message_content = self._fill_template(template)

        username = input("\n  Bot username (default: Toolkit Bot): ").strip() or "Toolkit Bot"
        avatar_url = input("  Avatar URL (optional, press Enter to skip): ").strip()

        payload = {
            "username": username,
            "content": message_content,
        }
        if avatar_url:
            payload["avatar_url"] = avatar_url

        console.print()
        console.print(Panel(Text(message_content, style="dim"), title=" Preview ", expand=False))

        confirm = input("\n  Send? (y/n): ").strip().lower()
        if confirm != "y":
            console.print("[yellow]↩  Not sent.[/yellow]")
            return

        try:
            response = requests.post(webhook_url, json=payload, timeout=15)
            if response.status_code in (200, 204, 201):
                console.print("[green]✓  Discord message sent successfully![/green]")
            else:
                console.print(
                    f"[red]✗  Discord API error: {response.status_code} {response.text[:200]}[/red]"
                )
        except requests.exceptions.ConnectionError:
            console.print("[red]✗  Could not connect to Discord webhook.[/red]")
        except Exception as exc:
            console.print(f"[red]✗  Failed to send: {exc}[/red]")
