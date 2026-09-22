"""Tool: QR Code Generator — generate QR codes as terminal ASCII art and PNG files."""
from __future__ import annotations

import io
from pathlib import Path

import qrcode
import questionary
from PIL import Image
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from utils.paths import get_downloads_dir, safe_filename

console = Console()


class QRGeneratorTool:
    """Generate QR codes from arbitrary text or URLs."""

    name: str = "QR Code Generator"
    description: str = "Generate terminal ASCII and PNG QR codes from text/URLs."
    icon: str = "📱"

    def run(self) -> None:
        console.print(
            Panel(Text("📱  QR Code Generator", style="bold cyan"), expand=False)
        )

        while True:
            data = questionary.text(
                "Enter text or URL to encode (or press Enter to return):"
            ).ask()

            if not data or data.strip().lower() in ("x", "q", "exit", "quit"):
                return

            self._generate(data.strip())

            again = questionary.confirm("Generate another QR code?", default=True).ask()
            if not again:
                return

    def _generate(self, data: str) -> None:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        console.print(
            f"\n[cyan]Generated QR code for:[/cyan] [bold]{data[:60]}{'...' if len(data) > 60 else ''}[/bold]"
        )

        # Render QR code as ASCII art in terminal
        buf = io.StringIO()
        qr.print_ascii(invert=True, tty=False, out=buf)
        ascii_art = buf.getvalue()

        console.print()
        console.print(Text(ascii_art, style="bold green"))
        console.print(f"[dim]({img.width}×{img.height} px image)[/dim]")

        # Save to file option
        save = questionary.confirm("Save QR code as image file?", default=False).ask()
        if save:
            slug = safe_filename(data[:25]) if data.isalnum() else "qr_code"
            default_path = str(get_downloads_dir() / f"{slug}.png")

            output_path_str = questionary.text(
                "Save path:",
                default=default_path,
            ).ask()

            if output_path_str:
                save_path = Path(output_path_str)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    img.save(str(save_path))
                    console.print(f"[green]✓ Saved image to: {save_path}[/green]")
                except Exception as exc:
                    console.print(f"[red]✗ Failed to save: {exc}[/red]")