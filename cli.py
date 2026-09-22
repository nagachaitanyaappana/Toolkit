from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from core.engine import (
    check_ffmpeg,
    extract_info,
    extract_playlist_info,
    get_best_quality,
    get_spotify_type,
    has_mixed_video_and_playlist,
    is_playlist,
    is_spotify_url,
    parse_range,
    run_download,
    run_download_playlist,
    strip_playlist_params,
)
from ui.menus import (
    select_audio_format,
    select_browser_cookies,
    select_playlist_mode,
    select_resolution,
)
from utils.validation import is_valid_url

PLATFORMS = {
    "youtube": ["youtube.com", "youtu.be"],
    "instagram": ["instagram.com"],
    "spotify": ["open.spotify.com", "spotify.link"],
    "pinterest": ["pinterest.com", "pin.it"],
    "twitter": ["twitter.com", "x.com"],
    "reddit": ["reddit.com", "redd.it"],
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Download videos/audio")
    parser.add_argument("url", nargs="?", help="Video URL or playlist")
    parser.add_argument("-t", "--type", choices=["video", "audio"], help="Download type")
    parser.add_argument("-r", "--resolution", choices=["best", "1080", "720", "480"], help="Video resolution")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output directory")
    args = parser.parse_args()

    console = Console()
    console.print(Panel(Text("🎬 Universal Downloader", style="bold magenta"), expand=False))

    if not check_ffmpeg():
        console.print(
            "[yellow]⚠️  Warning: FFmpeg is not installed. High-res stream merging may fail.[/yellow]"
        )

    url = args.url
    if not url:
        url = questionary.text("URL:").ask()
        if not url:
            return

    url = url.strip()
    if not is_valid_url(url):
        console.print("[red]Error:[/red] Please enter a valid URL.")
        sys.exit(1)

    # 1. Spotify handling
    if is_spotify_url(url):
        spotify_type = get_spotify_type(url)
        console.print(f"📌 Platform: [cyan]Spotify ({spotify_type.capitalize()})[/cyan]")

        output_dir = args.output
        base_dir = output_dir or Path.home() / "Downloads"

        if spotify_type in ("playlist", "album"):
            playlist_title = questionary.text("Enter playlist/album folder name:").ask() or "Spotify"
            spotify_dir = base_dir / playlist_title
        else:
            spotify_dir = base_dir / "Spotify"

        spotify_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"📁 Saving to: {spotify_dir}")
        console.print("⏳ Downloading from Spotify via spotdl...")

        try:
            import subprocess

            result = subprocess.run(
                [
                    "spotdl", "download", url,
                    "--output", str(spotify_dir),
                    "--format", "mp3",
                    "--threads", "6",
                    "--playlist-numbering",
                ],
                capture_output=True,
                text=True,
                timeout=7200,
            )

            if result.returncode != 0:
                stderr = result.stderr.lower()
                if "not accessible" in stderr or "not public" in stderr or "private" in stderr:
                    console.print("[red]Error:[/red] Playlist is private.")
                    sys.exit(1)
                elif "not found" in stderr:
                    console.print("[red]Error:[/red] Spotify track/playlist not found.")
                    sys.exit(1)
                else:
                    console.print(f"[red]Error:[/red] spotdl failed:\n{result.stderr[:400]}")
                    sys.exit(1)

        except FileNotFoundError:
            console.print("[red]Error:[/red] 'spotdl' is not installed.")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            console.print("[red]Error:[/red] Download timed out.")
            sys.exit(1)
        except Exception as exc:
            console.print(f"[red]Error:[/red] Download failed: {exc}")
            sys.exit(1)

        console.print("[green]✓ Spotify download complete![/green]")
        return

    platform = detect_platform(url)
    if platform != "unknown":
        console.print(f"📌 Platform: [cyan]{platform.capitalize()}[/cyan]")
    else:
        console.print("📌 Platform: [dim]Universal[/dim]")

    # Check mixed link
    is_playlist_flow = False
    if has_mixed_video_and_playlist(url):
        mode = select_playlist_mode()
        if not mode:
            return
        if mode == "single":
            url = strip_playlist_params(url)
        else:
            is_playlist_flow = True
    elif is_playlist(url):
        is_playlist_flow = True

    download_type = args.type
    if not download_type:
        download_type = questionary.select(
            "Download type:",
            choices=["Video", "Audio"],
        ).ask()
        if not download_type:
            return
        download_type = download_type.lower()

    resolution = args.resolution or "best"
    audio_format = "mp3"
    video_format = "mp4"

    if download_type == "video" and not args.resolution:
        res_choice = select_resolution()
        if not res_choice:
            return
        resolution = res_choice
    elif download_type == "audio":
        af_choice = select_audio_format()
        if not af_choice:
            return
        audio_format = af_choice

    output_dir = args.output

    if is_playlist_flow:
        console.print("⏳ Fetching playlist info...")
        try:
            playlist_info = extract_playlist_info(url)
        except Exception as exc:
            console.print(f"[red]Error:[/red] Failed to fetch playlist: {exc}")
            sys.exit(1)

        entries = playlist_info.get("entries", [])
        if not entries:
            console.print("[red]Error:[/red] No videos found in playlist.")
            sys.exit(1)

        playlist_title = playlist_info.get("title", "Playlist")
        console.print(f"📋 Playlist: [bold]{playlist_title}[/bold]")
        console.print(f"🎬 Total Items: [cyan]{len(entries)}[/cyan]")

        selected = select_videos_interactive(entries)
        if not selected:
            return

        if output_dir is None:
            output_dir = Path.home() / "Downloads" / playlist_title
        else:
            output_dir = output_dir / playlist_title
        output_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"📁 Saving to: {output_dir}")
        console.print(f"⬇ Downloading {len(selected)} items as {download_type} ({resolution})...")

        try:
            run_download_playlist(
                entries=selected,
                download_type=download_type,
                output_dir=output_dir,
                video_format=video_format,
                audio_format=audio_format,
                resolution=resolution,
            )
        except Exception as exc:
            console.print(f"[red]Error:[/red] Download failed: {exc}")
            sys.exit(1)

        console.print(f"[green]✓ Downloaded {len(selected)} items to {output_dir}[/green]")
    else:
        console.print("⏳ Fetching info...")
        try:
            info = extract_info(url)
        except Exception as exc:
            console.print(f"[red]Error:[/red] Failed to fetch video info: {exc}")
            sys.exit(1)

        title = info.get("title", "Unknown")
        quality = get_best_quality(info, download_type)
        duration = int(info.get("duration", 0) or 0)
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
        console.print(f"📹 Title: [bold]{title}[/bold]")
        console.print(f"🎥 Quality: [cyan]{quality}[/cyan]")
        if duration:
            console.print(f"⏱  Duration: [yellow]{duration_str}[/yellow]")

        try:
            run_download(
                url=url,
                download_type=download_type,
                video_format=video_format,
                audio_format=audio_format,
                resolution=resolution,
                output_dir=output_dir,
            )
        except Exception as exc:
            console.print(f"[red]Error:[/red] Download failed: {exc}")
            sys.exit(1)

        console.print("[green]✓ Download complete![/green]")


if __name__ == "__main__":
    main()
