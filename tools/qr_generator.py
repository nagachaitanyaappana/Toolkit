"""Tool: QR Code Generator — generate QR codes from text or URLs."""
from __future__ import annotations

import io

import qrcode
from PIL import Image
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


class QRGeneratorTool:
    """Generate QR codes from arbitrary text or URLs."""

    name: str = "QR Code Generator"
    description: str = "Generate QR codes from text or URLs."
    icon: str = "📱"

    def run(self) -> None:
        console.print(
            Panel(Text("📱  QR Code Generator", style="bold cyan"), expand=False)
        )

        while True:
            data = input("\n📋 Enter text or URL to encode (or press Enter to return): ").strip()
            if not data:
                console.print("[yellow]↩  Returning to menu.[/yellow]")
                return

            self._generate(data)

            again = input("\n  Generate another? (y/n): ").strip().lower()
            if again != "y":
                return

    def _generate(self, data: str) -> None:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        console.print(f"\n[cyan]Generated QR code for:[/cyan] {data[:50]}{'...' if len(data) > 50 else ''}")

                                # Render QR code as ASCII art in the terminal
        buf = io.StringIO()
        qr.print_ascii(invert=True, tty=False, out=buf)
        ascii_art = buf.getvalue()
        console.print()
        console.print(Text(ascii_art, style="bold green"))
        console.print(f"[dim]({img.width}×{img.height} px image generated)[/dim]")

        # Save to file option
        save = input("\n  Save QR code as image file? (y/n): ").strip().lower()
        if save == "y":
            from utils.paths import safe_filename

            filename = safe_filename(data[:30] if data.isalnum() else "qr_code") + ".png"
            output_path = input(f"  Save path (default: {filename}): ").strip()
            if not output_path:
                output_path = filename
            try:
                img.save(output_path)
                console.print(f"[green]✓ Saved to: {output_path}[/green]")
            except Exception as exc:
                console.print(f"[red]✗ Failed to save: {exc}[/red]")