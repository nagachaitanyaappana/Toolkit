"""Tool: Network Tool — ping hosts and scan ports."""
from __future__ import annotations

import socket
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# Common ports to scan
COMMON_PORTS = [
    20, 21, 22, 23, 25, 53, 67, 68, 69, 80,
    110, 111, 119, 123, 135, 137, 138, 139, 143, 161, 162, 389, 443,
    445, 465, 514, 515, 587, 631, 636, 873, 901, 989, 990, 993, 995,
    1433, 1521, 1522, 1723, 2049, 3306, 3389, 5432, 5800, 5900, 5984,
    6379, 6600, 6660, 6661, 6662, 6663, 6664, 6665, 6666, 6667, 6668,
    6669, 6697, 7001, 7002, 8000, 8008, 8080, 8081, 8443, 8888, 9090,
    9092, 9200, 9300, 11211, 15672, 27017, 27018, 27019, 50000, 50030,
]


class NetworkTool:
    """Ping hosts and scan for open ports."""

    name: str = "Network Tool"
    description: str = "Ping hosts and scan ports."
    icon: str = "🌐"

    def run(self) -> None:
        console.print(
            Panel(Text("🌐  Network Tool", style="bold cyan"), expand=False)
        )

        while True:
            console.print("\n[dim]Select an option:[/dim]")
            console.print("  1) Ping a host")
            console.print("  2) Port scan")
            console.print("  x) Return to menu")

            choice = input("\n▶  Select: ").strip().lower()

            if choice == "1":
                self._ping_host()
            elif choice == "2":
                self._port_scan()
            elif choice in ("x", "q", ""):
                return
            else:
                console.print("[red]✗  Invalid choice.[/red]")

    def _ping_host(self) -> None:
        host = input("\n📋 Enter hostname or IP to ping: ").strip()
        if not host:
            return

        count_str = input("  Packet count (default 4): ").strip()
        try:
            count = int(count_str) if count_str else 4
            count = min(max(count, 1), 20)
        except ValueError:
            count = 4

        console.print(f"\n[cyan]Pinging {host} ({count} packets)...[/cyan]\n")

        try:
            result = subprocess.run(
                ["ping", "-c", str(count), "-W", "2", host],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Print ping output lines that contain relevant info
            for line in result.stdout.splitlines():
                console.print(f"  {line}")
            if result.returncode == 0:
                console.print("[green]✓  Host is reachable.[/green]")
            else:
                console.print("[red]✗  Host is unreachable or timed out.[/red]")
        except FileNotFoundError:
            console.print("[red]✗  'ping' command not found on this system.[/red]")
        except subprocess.TimeoutExpired:
            console.print("[red]✗  Ping timed out.[/red]")
        except Exception as exc:
            console.print(f"[red]✗  Error: {exc}[/red]")

    def _port_scan(self) -> None:
        host = input("\n📋 Enter hostname or IP to scan: ").strip()
        if not host:
            return

        port_input = input("  Ports (e.g., 80,443,8080 or 'all' for common ports): ").strip()
        if not port_input:
            console.print("[yellow]↩  No input. Returning.[/yellow]")
            return

        if port_input.lower() == "all":
            ports = COMMON_PORTS
        else:
            ports = []
            for part in port_input.split(","):
                part = part.strip()
                if "-" in part:
                    try:
                        start, end = part.split("-")
                        ports.extend(range(int(start), int(end) + 1))
                    except ValueError:
                        pass
                elif part.isdigit():
                    ports.append(int(part))

        if not ports:
            console.print("[red]✗  No valid ports entered.[/red]")
            return

        console.print(f"\n[cyan]Scanning {host} ({len(ports)} ports)...[/cyan]\n")

        open_ports: list[tuple[int, str]] = []
        timeout = 1.0

        def scan_port(port: int) -> tuple[int, bool]:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(timeout)
                    result = sock.connect_ex((host, port))
                    return (port, result == 0)
            except Exception:
                return (port, False)

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = {executor.submit(scan_port, p): p for p in ports}
            for future in as_completed(futures):
                port, is_open = future.result()
                if is_open:
                    open_ports.append((port, "open"))

        if open_ports:
            table = Table(title=" Open Ports ", show_header=True, border_style="green")
            table.add_column("Port", justify="right", style="cyan")
            table.add_column("Status")
            for port, status in open_ports:
                table.add_row(str(port), f"[green]{status}[/green]")
            console.print()
            console.print(table)
            console.print(f"\n[green]✓  Found {len(open_ports)} open port(s).[/green]")
        else:
            console.print("[yellow]∄  No open ports found.[/yellow]")

        input("\n[Enter] to continue...")
