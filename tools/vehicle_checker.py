"""Tool: Vehicle Number Checker — validate and look up vehicle registration info."""
from __future__ import annotations

import re

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

FORMAT_PATTERNS = {
    "India": {
        "pattern": re.compile(
            r"^([A-Z]{2})\s*[- ]\s*([0-9]{1,3})\s*[- ]?\s*([A-Z]{1,3})\s*[- ]?\s*([0-9]{1,4})$",
            re.IGNORECASE,
        ),
        "description": "State-Code RTO-Code Letter-Series Numbers (e.g., MH-12-AB-1234)",
    },
    "USA": {
        "pattern": re.compile(r"^[A-Z0-9]{1,3}\s*[- ]\s*[A-Z0-9]{1,4}$", re.IGNORECASE),
        "description": "Alphanumeric with hyphen (e.g., ABC-1234)",
    },
    "UK": {
        "pattern": re.compile(r"^[A-Z]{2}[0-9][0-9A-Z]\s?[0-9][A-Z]{2}$", re.IGNORECASE),
        "description": "Format: AB51 ABC",
    },
    "Generic": {
        "pattern": re.compile(r"^[A-Z0-9\- ]{3,15}$", re.IGNORECASE),
        "description": "Alphanumeric with spaces/hyphens",
    },
}

INDIAN_STATES = {
    "AN": "Andaman and Nicobar Islands",
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CH": "Chandigarh",
    "CG": "Chhattisgarh",
    "DL": "Delhi",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HR": "Haryana",
    "HP": "Himachal Pradesh",
    "JK": "Jammu and Kashmir",
    "JH": "Jharkhand",
    "KA": "Karnataka",
    "KL": "Kerala",
    "MP": "Madhya Pradesh",
    "MH": "Maharashtra",
    "ML": "Meghalaya",
    "MZ": "Mizoram",
    "MN": "Manipur",
    "NL": "Nagaland",
    "OR": "Odisha",
    "PY": "Puducherry",
    "PB": "Punjab",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TN": "Tamil Nadu",
    "TR": "Tripura",
    "UP": "Uttar Pradesh",
    "UT": "Uttarakhand",
    "WB": "West Bengal",
    "TS": "Telangana",
}


class VehicleCheckerTool:
    """Check vehicle registration numbers against known formats and APIs."""

    name: str = "Vehicle Number Checker"
    description: str = "Check vehicle registration details by license plate."
    icon: str = "🚗"

    def run(self) -> None:
        console.print(
            Panel(Text("🚗  Vehicle Number Checker", style="bold cyan"), expand=False)
        )

        while True:
            number = input("\n📋 Enter vehicle registration number: ").strip()
            if not number:
                console.print("[yellow]↩  No input given. Returning to menu.[/yellow]")
                return

            self._check_number(number.upper())

            again = input("\n  Check another? (y/n): ").strip().lower()
            if again != "y":
                return

    def _check_number(self, raw: str) -> None:
        normalized = re.sub(r"\s+", " ", raw.strip())

        matched_country = None
        matched_data = None
        matched_format = None

        for country, info in FORMAT_PATTERNS.items():
            match = info["pattern"].match(normalized)
            if match:
                matched_country = country
                matched_format = info["description"]
                if country == "India":
                    matched_data = match.groups()
                break

        if not matched_country:
            console.print(f"[red]✗  '{normalized}' does not match any known format.[/red]")
            console.print(f"[dim]Supported countries: {', '.join(FORMAT_PATTERNS.keys())}[/dim]")
            return

        table = Table(title=" Vehicle Details ", show_header=False)
        table.add_column(style="cyan", no_wrap=True, max_width=20)
        table.add_column()

        table.add_row("Input", normalized)
        table.add_row("Country", matched_country)
        table.add_row("Format", matched_format)
        table.add_row("Valid", "[green]✓ Yes[/green]")

        if matched_country == "India" and matched_data:
            state_code = matched_data[0]
            rto_code = matched_data[1]
            series = matched_data[2]
            numbers = matched_data[3]
            state_name = INDIAN_STATES.get(state_code, "Unknown State")
            table.add_row("State Code", state_code)
            table.add_row("State", state_name)
            table.add_row("RTO Code", rto_code)
            table.add_row("Series", series)
            table.add_row("Numbers", numbers)

        console.print()
        console.print(table)
        self._try_api_lookup(normalized)

    def _try_api_lookup(self, number: str) -> None:
        clean = re.sub(r"[^A-Z0-9]", "", number.upper())

        try:
            response = requests.post(
                "https://vahanapi.in/api/vehicle",
                data={"registration_number": clean},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self._display_api_results(data.get("data", {}))
                    return
        except Exception:
            pass

        try:
            response = requests.post(
                "https://vahanapi.in/api/vehicle-rc",
                data={"regn_num": clean},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    self._display_api_results(data.get("data", {}))
                    return
        except Exception:
            pass

        console.print()
        console.print(
            "[dim]ℹ️  Advanced API lookup unavailable. "
            "Basic format validation shown above.[/dim]"
        )

    def _display_api_results(self, data: dict) -> None:
        if not data:
            return

        console.print()
        console.print("[bold cyan]📋  API Lookup Results:[/bold cyan]")
        table = Table(title=" Additional Details ", show_header=False)
        table.add_column(style="cyan", no_wrap=True, max_width=22)
        table.add_column()

        fields = [
            ("Owner Name", "owner_name"),
            ("Father's Name", "father_name"),
            ("Vehicle Class", "vehicle_class"),
            ("Maker", "maker"),
            ("Model", "model"),
            ("Engine No.", "engine_number"),
            ("Chassis No.", "chassis_number"),
            ("Registration Date", "registration_date"),
            ("Fuel Type", "fuel_type"),
            ("Insurance Upto", "insurance_upto"),
            ("PUC Expiry", "pucc_expiry"),
        ]

        for label, key in fields:
            value = data.get(key, "-")
            if value:
                table.add_row(label, str(value))

        console.print(table)
