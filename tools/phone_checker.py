"""Tool: Phone Number Checker — validate phone numbers, get carrier/location info, and look up Caller ID & Spam Risk via Truecaller."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import phonenumbers
from phonenumbers import (
    PhoneNumberType,
    carrier,
    geocoder,
    number_type,
    timezone,
)
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

CONFIG_DIR = Path.home() / ".config" / "toolkit"
TRUECALLER_AUTH_FILE = CONFIG_DIR / "truecaller_auth.json"


def load_truecaller_session() -> dict | None:
    """Load saved Truecaller installation ID if available."""
    if not TRUECALLER_AUTH_FILE.exists():
        return None
    try:
        with open(TRUECALLER_AUTH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("installation_id"):
                return data
    except Exception:
        return None
    return None


def save_truecaller_session(installation_id: str, phone_number: str = "") -> None:
    """Save Truecaller installation ID securely with 0600 permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "installation_id": installation_id.strip(),
        "phone_number": phone_number.strip(),
    }
    with open(TRUECALLER_AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        os.chmod(TRUECALLER_AUTH_FILE, 0o600)
    except Exception:
        pass


def delete_truecaller_session() -> None:
    """Remove Truecaller session on logout."""
    if TRUECALLER_AUTH_FILE.exists():
        try:
            TRUECALLER_AUTH_FILE.unlink()
        except Exception:
            pass


async def query_truecaller(
    number: str, country_code: str, installation_id: str
) -> dict | None:
    """Query Truecaller API for Caller ID and spam score."""
    try:
        import truecallerpy

        res = await truecallerpy.search_phonenumber(
            number, country_code, installation_id
        )
        if res.get("status_code") == 200 and res.get("data"):
            data_list = res["data"].get("data", [])
            if data_list:
                return data_list[0]
    except Exception:
        return None
    return None


class PhoneCheckerTool:
    """Validate phone numbers and retrieve carrier, location, WhatsApp link, Caller Name, and spam risk."""

    name: str = "Phone Number Checker"
    description: str = "Check phone numbers for validity, carrier, Caller ID, and spam risk."
    icon: str = "📞"

    def run(self) -> None:
        console.print(
            Panel(
                Text("📞  Phone Number & Caller ID Checker", style="bold cyan"),
                expand=False,
            )
        )

        while True:
            session = load_truecaller_session()

            raw = questionary.text(
                "Enter phone number (e.g. 9876543210 or +91 9876543210, or leave blank to return):"
            ).ask()

            if not raw or raw.strip().lower() in ("x", "q", "exit", "quit"):
                return

            self._process_number(raw.strip())

            again = questionary.confirm("Check another number?", default=True).ask()
            if not again:
                return

    def _process_number(self, cleaned: str) -> None:
        # Default to India (IN) for standard 10-digit numbers
        try:
            if cleaned.startswith("+"):
                parsed = phonenumbers.parse(cleaned)
            else:
                parsed = phonenumbers.parse(cleaned, "IN")
        except phonenumbers.NumberParseException as exc:
            console.print(f"\n[red]✗  Invalid phone number: {exc}[/red]\n")
            return

        is_valid = phonenumbers.is_valid_number(parsed)
        is_possible = phonenumbers.is_possible_number(parsed)
        national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        international = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        country_code = phonenumbers.region_code_for_number(parsed) or "IN"
        dialing_code = str(parsed.country_code)

        carrier_name = carrier.name_for_number(parsed, "en") or "Unknown"
        location = geocoder.description_for_number(parsed, "en") or "Unknown"
        time_zones = timezone.time_zones_for_number(parsed)
        tz_str = ", ".join(time_zones) if time_zones else "Unknown"

        num_type = number_type(parsed)
        type_label = {
            PhoneNumberType.MOBILE: "Mobile",
            PhoneNumberType.FIXED_LINE: "Fixed Line",
            PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed / Mobile",
            PhoneNumberType.TOLL_FREE: "Toll-Free",
            PhoneNumberType.SHARED_COST: "Shared Cost",
            PhoneNumberType.VOIP: "VoIP (Virtual / Internet)",
            PhoneNumberType.PERSONAL_NUMBER: "Personal Number",
            PhoneNumberType.PAGER: "Pager",
            PhoneNumberType.UAN: "UAN",
            PhoneNumberType.VOICEMAIL: "Voicemail",
        }.get(num_type, "Unknown")

        # Heuristic Risk Assessment
        if not is_valid:
            risk_label = "[bold red]🛑 High Risk (Invalid / Spoofed)[/bold red]"
        elif num_type == PhoneNumberType.VOIP:
            risk_label = "[bold yellow]⚠️ Moderate Risk (VoIP line — common in virtual/internet calls)[/bold yellow]"
        elif num_type in (PhoneNumberType.TOLL_FREE, PhoneNumberType.SHARED_COST):
            risk_label = "[bold yellow]⚠️ Commercial / Telemarketing[/bold yellow]"
        else:
            risk_label = "[bold green]🟢 Low Risk (Standard Carrier Line)[/bold green]"

        # Direct WhatsApp Clickable Link
        digits_only = f"{parsed.country_code}{parsed.national_number}"
        wa_link = f"https://wa.me/{digits_only}"

        # Check Truecaller session
        session = load_truecaller_session()
        tc_data = None

        if session and is_valid:
            console.print("\n⏳ [cyan]Querying Truecaller Caller ID & Spam Score...[/cyan]")
            try:
                tc_data = asyncio.run(
                    query_truecaller(
                        str(parsed.national_number),
                        country_code,
                        session["installation_id"],
                    )
                )
            except Exception:
                tc_data = None

        # Build Rich Table
        table = Table(title=" Phone Number Analysis ", show_header=False, border_style="cyan")
        table.add_column("Property", style="cyan bold", no_wrap=True, max_width=22)
        table.add_column("Details")

        if tc_data:
            caller_name = tc_data.get("name")
            if caller_name:
                table.add_row("Caller Name", f"[bold green]{caller_name}[/bold green]")
            else:
                table.add_row("Caller Name", "[dim]Name not listed in Truecaller[/dim]")

            spam_score = tc_data.get("spamScore", 0)
            spam_type = tc_data.get("spamType") or ""
            if spam_score and int(spam_score) > 0:
                spam_str = f"[bold red]🚨 HIGH SPAM RISK ({spam_score} reports)[/bold red]"
                if spam_type:
                    spam_str += f" [red]({spam_type})[/red]"
                table.add_row("Truecaller Spam", spam_str)
            else:
                table.add_row("Truecaller Spam", "[bold green]✓ Clean / 0 Spam Reports[/bold green]")

            addresses = tc_data.get("addresses", [])
            if addresses:
                city = addresses[0].get("city")
                if city:
                    table.add_row("City", city)
        else:
            if session:
                table.add_row("Caller Name", "[dim]No Truecaller record found[/dim]")
            else:
                table.add_row("Caller Name", "[yellow]🔒 Not Connected (Connect Truecaller below to view)[/yellow]")
                table.add_row("Truecaller Spam", "[yellow]🔒 Not Connected[/yellow]")

        table.add_row("Risk Assessment", risk_label)
        table.add_row("Validity", "[green]✓ Valid[/green]" if is_valid else "[red]✗ Invalid[/red]")
        table.add_row("Line Type", type_label)
        table.add_row("Carrier", f"[bold]{carrier_name}[/bold]")
        table.add_row("Region / Circle", location)
        table.add_row("National", national)
        table.add_row("International", international)
        table.add_row("Country Code", f"+{dialing_code} ({country_code})")
        table.add_row("Timezone", tz_str)
        table.add_row("WhatsApp Chat", f"[underline blue]{wa_link}[/underline blue]")

        console.print()
        console.print(table)
        console.print()

        # If Truecaller is not connected, offer 1-time setup right here
        if not session and is_valid:
            connect = questionary.confirm(
                "🔑 Would you like to connect Truecaller to reveal this person's name?",
                default=False,
            ).ask()
            if connect:
                if self._connect_truecaller_flow():
                    # Re-run for this number immediately with newly saved session!
                    self._process_number(cleaned)

    def _connect_truecaller_flow(self) -> bool:
        console.print("\n[bold cyan]🔑  Connect Truecaller (1-Time Setup)[/bold cyan]")
        console.print("[dim]Truecaller will send a 6-digit OTP to your phone to generate your access token.[/dim]\n")

        my_phone = questionary.text(
            "Enter your mobile number with country code (e.g. +919876543210):",
            validate=lambda x: x.startswith("+") and len(x.strip()) >= 10,
        ).ask()
        if not my_phone:
            return False

        import truecallerpy

        console.print("\n⏳ [cyan]Requesting OTP from Truecaller...[/cyan]")
        try:
            res = asyncio.run(truecallerpy.login(my_phone.strip()))
        except Exception as exc:
            console.print(f"[red]✗  Failed to request OTP: {exc}[/red]")
            return False

        if res.get("status_code") not in (200, 201) or not res.get("data"):
            msg = res.get("message") or res.get("data", {}).get("message") or "Unknown error"
            console.print(f"[red]✗  Truecaller error: {msg}[/red]")
            return False

        json_data = res["data"]
        console.print("[green]✓  OTP sent! Check your SMS or Truecaller notification.[/green]")

        otp = questionary.text(
            "Enter the 6-digit OTP:",
            validate=lambda x: len(x.strip()) >= 4,
        ).ask()
        if not otp:
            return False

        console.print("\n⏳ [cyan]Verifying OTP...[/cyan]")
        try:
            verify_res = asyncio.run(truecallerpy.verify_otp(my_phone.strip(), json_data, otp.strip()))
        except Exception as exc:
            console.print(f"[red]✗  Verification failed: {exc}[/red]")
            return False

        if verify_res.get("status_code") in (200, 201) and verify_res.get("data"):
            install_id = verify_res["data"].get("installationId")
            if install_id:
                save_truecaller_session(install_id, my_phone.strip())
                console.print(f"\n[bold green]✓  Successfully connected to Truecaller![/bold green]")
                console.print("[dim]Fetching Caller Name & Spam Score now...[/dim]\n")
                return True

        err = verify_res.get("message") or verify_res.get("data", {}).get("message") or "Verification failed."
        console.print(f"[red]✗  {err}[/red]")
        return False