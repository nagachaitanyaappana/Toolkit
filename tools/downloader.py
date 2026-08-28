"""Tool: URL Downloader — downloads videos/audio from various platforms."""
from __future__ import annotations

from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from core.engine import (
    extract_info,
    extract_playlist_info,
    get_best_quality,
    is_playlist,
    is_spotify_playlist,
    parse_range,
    run_download,
    run_download_playlist,
)
from utils.validation import is_valid_url

console = Console()

PLATFORMS = {
    "youtube": ["youtube.com", "youtu.be"],
    "twitch": ["twitch.tv", "clips.twitch.tv"],
    "instagram": ["instagram.com"],
    "facebook": ["facebook.com", "fb.watch"],
    "tiktok": ["tiktok.com"],
    "twitter": ["twitter.com", "x.com"],
    "reddit": ["reddit.com", "redd.it"],
    "vimeo": ["vimeo.com"],
    "soundcloud": ["soundcloud.com"],
    "spotify": ["open.spotify.com"],
}


def detect_platform(url: str) -> str:
    url_lower = url.lower()
    for platform, domains in PLATFORMS.items():
        for domain in domains:
            if domain in url_lower:
                return platform
    return "unknown"


def select_videos_interactive(entries: list[dict]) -> list[dict]:
    choices = [
        {"name": "All videos", "value": "all"},
        {"name": "Range (e.g., 1-5)", "value": "range"},
        {"name": "Select individual", "value": "individual"},
    ]
    choice = questionary.select("Select videos:", choices=choices).ask()
    if not choice:
        return []

    if choice == "all":
        return entries

    if choice == "range":
        range_str = questionary.text("Enter range (e.g., 1-5, 1,3,5):").ask()
        if not range_str:
            return []
        indices = parse_range(range_str, len(entries))
        return [entries[i - 1] for i in indices if 1 <= i <= len(entries)]

    if choice == "individual":
        video_choices = [
            {
                "name": f"{i + 1}. {entry.get('title', 'Unknown')}",
                "value": i,
                "checked": False,
            }
            for i, entry in enumerate(entries)
        ]
        selected = questionary.checkbox("Select videos:", choices=video_choices).ask()
        if not selected:
            return []
        return [entries[i] for i in selected]

    return []


class DownloaderTool:
    """Download videos and audio from video-sharing platforms."""

    name: str = "URL Downloader"
    description: str = "Download videos/audio from YouTube, TikTok, etc."
    icon: str = "📱"

    def run(self) -> None:
        console.print(
            Panel(Text("🎬  URL Downloader", style="bold magenta"), expand=False)
        )

        url = questionary.text("URL:").ask()
        if not url:
            return

        if not is_valid_url(url):
            console.print("[red]Error:[/red] Please enter a valid URL.")
            return

        output_dir_str = questionary.text(
            "Output directory (leave blank for Downloads):"
        ).ask()
        output_dir = Path(output_dir_str) if output_dir_str else None

        if is_spotify_playlist(url):
            self._download_spotify(url, output_dir)
            return

        platform = detect_platform(url)
        if platform != "unknown":
            console.print(f"📌 Platform: [cyan]{platform.capitalize()}[/cyan]")

        download_type = questionary.select(
            "Download type:",
            choices=["Video", "Audio"],
        ).ask()
        if not download_type:
            return
        download_type = download_type.lower()

        if is_playlist(url):
            self._download_playlist(
                url=url,
                download_type=download_type,
                output_dir=output_dir,
            )
        else:
            self._download_single(
                url=url,
                download_type=download_type,
                output_dir=output_dir,
            )

    def _download_spotify(self, url: str, output_dir: Path | None) -> None:
        import subprocess

        base_dir = output_dir or Path.home() / "Downloads"

        playlist_title = questionary.text(
            "Enter playlist folder name:"
        ).ask()
        if not playlist_title:
            playlist_title = "Spotify Playlist"

        spotify_dir = base_dir / playlist_title
        spotify_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"📁 Saving to: {spotify_dir}")
        console.print("⏳ Downloading from Spotify via YouTube...")

        try:
            result = subprocess.run(
                [
                    "spotdl", "download", url,
                    "--output", str(spotify_dir),
                    "--format", "mp3",
                    "--threads", "8",
                    "--audio", "youtube",
                ],
                capture_output=True,
                text=True,
                timeout=7200,
            )

            if result.returncode != 0:
                stderr = result.stderr.lower()
                if "not accessible" in stderr or "not public" in stderr or "private" in stderr:
                    console.print("[red]Error:[/red] Playlist is private.")
                    console.print("Make it public in Spotify settings, or use a public playlist URL.")
                elif "not found" in stderr:
                    console.print("[red]Error:[/red] Playlist not found.")
                else:
                    console.print(f"[red]Error:[/red] spotdl failed:\n{result.stderr[:500]}")
        except subprocess.TimeoutExpired:
            console.print("[red]Error:[/red] Download timed out.")
        except FileNotFoundError:
            console.print("[red]Error:[/red] 'spotdl' is not installed. Install via: pip install spotdl")
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            return

        console.print("[green]✓ Spotify playlist download complete![/green]")

    def _download_playlist(
        self,
        url: str,
        download_type: str,
        output_dir: Path | None,
    ) -> None:
        console.print("⏳ Fetching playlist info...")
        try:
            playlist_info = extract_playlist_info(url)
        except Exception as exc:
            console.print(f"[red]Error:[/red] Failed to fetch playlist: {exc}")
            return

        entries = playlist_info.get("entries", [])
        if not entries:
            console.print("[red]Error:[/red] No videos found in playlist.")
            return

        playlist_title = playlist_info.get("title", "Playlist")
        console.print(f"📋 Playlist: [bold]{playlist_title}[/bold]")
        console.print(f"🎬 Videos: [cyan]{len(entries)}[/cyan]")

        selected = select_videos_interactive(entries)
        if not selected:
            return

        if output_dir is None:
            output_dir = Path.home() / "Downloads" / playlist_title
        else:
            output_dir = output_dir / playlist_title
        output_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"📁 Saving to: {output_dir}")
        console.print(f"⬇  Downloading {len(selected)} videos as {download_type}...")

        try:
            run_download_playlist(
                entries=selected,
                download_type=download_type,
                output_dir=output_dir,
                video_format="mp4",
                audio_format="mp3",
            )
        except Exception as exc:
            console.print(f"[red]Error:[/red] Download failed: {exc}")
            return

        console.print(
            f"[green]✓ Downloaded {len(selected)} videos to {output_dir}[/green]"
        )

    def _download_single(
        self,
        url: str,
        download_type: str,
        output_dir: Path | None,
    ) -> None:
        console.print("⏳ Fetching info...")
        try:
            info = extract_info(url)
        except Exception as exc:
            console.print(f"[red]Error:[/red] Failed to fetch video info: {exc}")
            return

        title = info.get("title", "Unknown")
        quality = get_best_quality(info, download_type)
        duration = int(info.get("duration", 0))
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = (
            f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            if hours
            else f"{minutes:02d}:{seconds:02d}"
        )
        console.print(f"📹 Title: [bold]{title}[/bold]")
        console.print(f"🎥 Quality: [cyan]{quality}[/cyan]")
        console.print(f"⏱  Duration: [yellow]{duration_str}[/yellow]")

        try:
            run_download(
                url=url,
                download_type=download_type,
                video_format="mp4",
                audio_format="mp3",
                output_dir=output_dir,
            )
        except Exception as exc:
            console.print(f"[red]Error:[/red] Download failed: {exc}")
            return

        console.print("[green]✓ Download complete![/green]")
