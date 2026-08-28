"""Tool: System Info Checker — display CPU, RAM, disk, and OS information."""
from __future__ import annotations

import platform
import shutil

import psutil
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


class SysInfoTool:
    """Display system hardware and OS information."""

    name: str = "System Info Checker"
    description: str = "Display CPU, RAM, disk, and OS information."
    icon: str = "💻"

    def run(self) -> None:
        console.print(
            Panel(Text("💻  System Info Checker", style="bold cyan"), expand=False)
        )

        # --- OS / Platform Info ---
        uname = platform.uname()
        boot_time = psutil.boot_time()
        import datetime
        boot_dt = datetime.datetime.fromtimestamp(boot_time).strftime("%Y-%m-%d %H:%M:%S")

        os_table = Table(title=" OS Information ", show_header=False, border_style="cyan")
        os_table.add_column(style="dim", no_wrap=True)
        os_table.add_column()
        os_table.add_row("System", uname.system)
        os_table.add_row("Node", uname.node)
        os_table.add_row("Release", uname.release)
        os_table.add_row("Version", uname.version)
        os_table.add_row("Machine", uname.machine)
        os_table.add_row("Processor", uname.processor or "N/A")
        os_table.add_row("Boot Time", boot_dt)
        os_table.add_row("Python", platform.python_version())
        console.print()
        console.print(os_table)

        # --- CPU Info ---
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        cpu_freq = psutil.cpu_freq()

        cpu_table = Table(title=" CPU Information ", show_header=False, border_style="cyan")
        cpu_table.add_column(style="dim", no_wrap=True)
        cpu_table.add_column()
        cpu_table.add_row("Usage", f"{cpu_percent}%")
        cpu_table.add_row("Logical Cores", str(cpu_count_logical))
        cpu_table.add_row("Physical Cores", str(cpu_count_physical))
        if cpu_freq:
            cpu_table.add_row("Min Freq", f"{cpu_freq.min:.0f} MHz")
            cpu_table.add_row("Max Freq", f"{cpu_freq.max:.0f} MHz")
            cpu_table.add_row("Current Freq", f"{cpu_freq.current:.0f} MHz")

        # Per-core usage
        core_percents = psutil.cpu_percent(interval=0.5, percpu=True)
        for i, pct in enumerate(core_percents):
            cpu_table.add_row(f"Core {i}", f"{pct}%")

        console.print()
        console.print(cpu_table)

        # --- Memory Info ---
        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()

        mem_table = Table(title=" Memory Information ", show_header=False, border_style="cyan")
        mem_table.add_column(style="dim", no_wrap=True)
        mem_table.add_column()
        mem_table.add_row("Total", f"{_fmt_bytes(vm.total)}")
        mem_table.add_row("Available", f"{_fmt_bytes(vm.available)}")
        mem_table.add_row("Used", f"{_fmt_bytes(vm.used)} ({vm.percent}%)")
        mem_table.add_row("Free", f"{_fmt_bytes(vm.free)}")
        if sm.total:
            mem_table.add_row("Swap Total", f"{_fmt_bytes(sm.total)}")
            mem_table.add_row("Swap Used", f"{_fmt_bytes(sm.used)} ({sm.percent}%)")
        console.print()
        console.print(mem_table)

        # --- Disk Info ---
        disks = psutil.disk_partitions()
        disk_table = Table(title=" Disk Information ", show_header=True, border_style="cyan")
        disk_table.add_column("Device", style="dim")
        disk_table.add_column("Mount")
        disk_table.add_column("FS-Type")
        disk_table.add_column("Total", justify="right")
        disk_table.add_column("Used", justify="right")
        disk_table.add_column("Free", justify="right")
        disk_table.add_column("Usage", justify="right")

        for d in disks:
            try:
                usage = psutil.disk_usage(d.mountpoint)
                disk_table.add_row(
                    d.device,
                    d.mountpoint,
                    d.fstype,
                    _fmt_bytes(usage.total),
                    _fmt_bytes(usage.used),
                    _fmt_bytes(usage.free),
                    f"{usage.percent}%",
                )
            except PermissionError:
                continue

        console.print()
        console.print(disk_table)

        # --- Network Info ---
        net = psutil.net_io_counters()
        net_table = Table(title=" Network Summary ", show_header=False, border_style="cyan")
        net_table.add_column(style="dim", no_wrap=True)
        net_table.add_column()
        net_table.add_row("Bytes Sent", _fmt_bytes(net.bytes_sent))
        net_table.add_row("Bytes Received", _fmt_bytes(net.bytes_recv))
        net_table.add_row("Packets Sent", str(net.packets_sent))
        net_table.add_row("Packets Received", str(net.packets_recv))
        console.print()
        console.print(net_table)

        # --- Process Summary ---
        procs = list(psutil.process_iter())
        console.print()
        console.print(f"[dim]🔄  Running processes: {len(procs)}[/dim]")

        input("\n[Enter] to return to menu...")


def _fmt_bytes(n: int) -> str:
    """Format byte count as human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"
