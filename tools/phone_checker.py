"""Tool: Phone Number Checker — validate and get info about phone numbers."""
from __future__ import annotations

import phonenumbers
from phonenumbers import (
    carrier,
    geocoder,
    number_type,
    PhoneNumberType,
)
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


class PhoneCheckerTool:
    """Validate phone numbers and retrieve carrier/location info."""

    name: str = "Phone Number Checker"
    description: str = "Validate phone numbers and get carrier/location info."
    icon: str = "📞"

    def run(self) -> None:
        console.print(
            Panel(Text("📞  Phone Number Checker", style="bold cyan"), expand=False)
        )

        while True:
            number = input("\n📋 Enter phone number (with country code e.g. +15551234567): ").strip()
            if not number:
                console.print("[yellow]↩  No input given. Returning to menu.[/yellow]")
                return

            self._check_number(number)

            again = input("\n  Check another? (y/n): ").strip().lower()
            if again != "y":
                return

    def _check_number(self, raw: str) -> None:
        try:
            parsed = phonenumbers.parse(raw)
        except phonenumbers.NumberParseException as exc:
            console.print(f"[red]✗  Invalid number: {exc}[/red]")
            return

        is_valid = phonenumbers.is_valid_number(parsed)
        is_possible = phonenumbers.is_possible_number(parsed)
        national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        international = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        country_code = phonenumbers.region_code_for_number(parsed)

        carrier_name = carrier.name_for_number(parsed, "en") or "Unknown"
        location = geocoder.description_for_number(parsed, "en") or "Unknown"

        num_type = number_type(parsed)
        type_label = {
            PhoneNumberType.MOBILE: "Mobile",
            PhoneNumberType.FIXED_LINE: "Fixed line",
            PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed/Mobile",
            PhoneNumberType.TOLL_FREE: "Toll-free",
            PhoneNumberType.SHARED_COST: "Shared cost",
            PhoneNumberType.VOIP: "VoIP",
            PhoneNumberType.PERSONAL_NUMBER: "Personal number",
            PhoneNumberType.PAGER: "Pager",
            PhoneNumberType.UAN: "UAN",
            PhoneNumberType.VOICEMAIL: "Voicemail",
        }.get(num_type, "Unknown")

        valid_str = "[green]✓ Valid[/green]" if is_valid else "[red]✗ Invalid[/red]"
        possible_str = "[green]Yes[/green]" if is_possible else "[red]No[/red]"

        table = Table(title=" Phone Number Details ", show_header=False)
        table.add_column(style="cyan", no_wrap=True)
        table.add_column()

        table.add_row("Valid", valid_str)
        table.add_row("Possible", possible_str)
        table.add_row("Type", type_label)
        table.add_row("National", national)
        table.add_row("International", international)
        table.add_row("Country Code", country_code or "N/A")
        table.add_row("Location", location)
        table.add_row("Carrier", carrier_name)

        console.print()
        console.print(table)