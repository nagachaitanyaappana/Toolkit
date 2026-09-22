"""Tool: URL Downloader — high quality media downloader for YouTube, Instagram, Spotify, Pinterest, X, and Reddit."""
from __future__ import annotations

import subprocess
from pathlib import Path

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

console = Console()

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


class DownloaderTool:
    """Download videos and audio from YouTube, Instagram, Spotify, Pinterest, X, and Reddit."""

    name: str = "URL Downloader"
    description: str = "Download media from YouTube, Instagram, Spotify, Pinterest, X, Reddit."
    icon: str = "🎬"

    def run(self) -> None:
        console.print(
            Panel(Text("🎬  Universal Media Downloader", style="bold magenta"), expand=False)
        )

        if not check_ffmpeg():
            console.print(
                "[yellow]⚠️  FFmpeg is not installed on this system.\n"
                "   Stream merging and audio conversion may fail.\n"
                "   Please install ffmpeg (e.g., sudo apt install ffmpeg).[/yellow]\n"
            )

        url = questionary.text("URL:").ask()
        if not url:
            return

        url = url.strip()
        if not is_valid_url(url):
            console.print("[red]✗ Error:[/red] Please enter a valid URL.")
            return

        platform = detect_platform(url)
        if platform != "unknown":
            console.print(f"📌 Platform: [bold cyan]{platform.capitalize()}[/bold cyan]")
        else:
            console.print("📌 Platform: [dim]Universal / Other[/dim]")

        # 1. Check for Spotify
        if is_spotify_url(url):
            self._download_spotify(url)
            return

        # 2. Check for mixed video + playlist (e.g. YouTube watch?v=...&list=...)
        is_playlist_flow = False
        if has_mixed_video_and_playlist(url):
            mode = select_playlist_mode()
            if not mode:
                return
            if mode == "single":
                url = strip_playlist_params(url)
                is_playlist_flow = False
            else:
                is_playlist_flow = True
        elif is_playlist(url):
            is_playlist_flow = True

        # 3. Choose Video or Audio
        download_type = questionary.select(
            "Download type:",
            choices=["Video", "Audio"],
        ).ask()
        if not download_type:
            return
        download_type = download_type.lower()

        # 4. Choose Resolution or Audio Format
        resolution = "best"
        audio_format = "mp3"
        video_format = "mp4"

        if download_type == "video":
            res_choice = select_resolution()
            if not res_choice:
                return
            resolution = res_choice
        else:
            af_choice = select_audio_format()
            if not af_choice:
                return
            audio_format = af_choice

        # 5. Output directory
        output_dir_str = questionary.text(
            "Output directory (leave blank for ~/Downloads):"
        ).ask()
        output_dir = Path(output_dir_str) if output_dir_str else None

        # 6. Execute download flow
        if is_playlist_flow:
            self._download_playlist(
                url=url,
                download_type=download_type,
                output_dir=output_dir,
                resolution=resolution,
                video_format=video_format,
                audio_format=audio_format,
            )
        else:
            self._download_single(
                url=url,
                download_type=download_type,
                output_dir=output_dir,
                resolution=resolution,
                video_format=video_format,
                audio_format=audio_format,
            )

    def _download_spotify(self, url: str) -> None:
        spotify_type = get_spotify_type(url)
        console.print(f"🎵 Spotify Type: [bold green]{spotify_type.capitalize()}[/bold green]")

        af_choice = select_audio_format()
        if not af_choice:
            af_choice = "mp3"

        base_dir = Path.home() / "Downloads"
        if spotify_type in ("playlist", "album"):
            default_folder = f"Spotify_{spotify_type.capitalize()}"
            folder_name = questionary.text(
                f"Enter {spotify_type} folder name:",
                default=default_folder,
            ).ask()
            spotify_dir = base_dir / (folder_name or default_folder)
        else:
            spotify_dir = base_dir / "Spotify"

        spotify_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"📁 Saving to: [cyan]{spotify_dir}[/cyan]")
        console.print("⏳ Fetching and downloading via spotdl...")

        cmd = [
            "spotdl",
            "download",
            url,
            "--output",
            str(spotify_dir),
            "--format",
            af_choice,
            "--threads",
            "6",
            "--playlist-numbering",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=7200,
            )

            if result.returncode != 0:
                stderr = result.stderr.lower()
                if "not accessible" in stderr or "private" in stderr:
                    console.print("[red]✗ Error:[/red] This Spotify content is private.")
                    console.print("Make sure the playlist is public or check the URL.")
                elif "not found" in stderr:
                    console.print("[red]✗ Error:[/red] Spotify track or playlist not found.")
                else:
                    console.print(f"[red]✗ spotdl error:[/red]\n{result.stderr[:400]}")
                return
        except FileNotFoundError:
            console.print("[red]✗ Error:[/red] 'spotdl' is not installed or not found in PATH.")
            console.print("Install via: pip install spotdl")
            return
        except subprocess.TimeoutExpired:
            console.print("[red]✗ Error:[/red] Download timed out.")
            return
        except Exception as exc:
            console.print(f"[red]✗ Error:[/red] {exc}")
            return

        console.print(f"\n[green]✓  Spotify download complete! Saved to {spotify_dir}[/green]")

    def _download_playlist(
        self,
        url: str,
        download_type: str,
        output_dir: Path | None,
        resolution: str,
        video_format: str,
        audio_format: str,
        browser_cookies: str | None = None,
    ) -> None:
        console.print("⏳ Fetching playlist info...")
        try:
            playlist_info = extract_playlist_info(url, browser_cookies=browser_cookies)
        except Exception as exc:
            if self._should_offer_cookies(str(exc)) and not browser_cookies:
                cookie_browser = select_browser_cookies()
                if cookie_browser and cookie_browser != "none":
                    return self._download_playlist(
                        url=url,
                        download_type=download_type,
                        output_dir=output_dir,
                        resolution=resolution,
                        video_format=video_format,
                        audio_format=audio_format,
                        browser_cookies=cookie_browser,
                    )
            console.print(f"[red]✗ Error:[/red] Failed to fetch playlist: {exc}")
            return

        entries = playlist_info.get("entries", [])
        if not entries:
            console.print("[red]✗ Error:[/red] No videos found in playlist.")
            return

        playlist_title = playlist_info.get("title", "Playlist")
        console.print(f"📋 Playlist: [bold]{playlist_title}[/bold]")
        console.print(f"🎬 Total Items: [cyan]{len(entries)}[/cyan]")

        selected = select_videos_interactive(entries)
        if not selected:
            return

        base_dir = output_dir or Path.home() / "Downloads"
        target_dir = base_dir / playlist_title
        target_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"📁 Saving to: [cyan]{target_dir}[/cyan]")
        console.print(
            f"⬇  Downloading {len(selected)} items as [cyan]{download_type.upper()}[/cyan] ({resolution})..."
        )

        try:
            run_download_playlist(
                entries=selected,
                download_type=download_type,
                output_dir=target_dir,
                video_format=video_format,
                audio_format=audio_format,
                resolution=resolution,
                browser_cookies=browser_cookies,
            )
        except Exception as exc:
            if self._should_offer_cookies(str(exc)) and not browser_cookies:
                cookie_browser = select_browser_cookies()
                if cookie_browser and cookie_browser != "none":
                    return self._download_playlist(
                        url=url,
                        download_type=download_type,
                        output_dir=output_dir,
                        resolution=resolution,
                        video_format=video_format,
                        audio_format=audio_format,
                        browser_cookies=cookie_browser,
                    )
            console.print(f"\n[red]✗ Error:[/red] Download failed: {exc}")
            return

        console.print(f"\n[green]✓ Successfully downloaded {len(selected)} items to {target_dir}[/green]")

    def _download_single(
        self,
        url: str,
        download_type: str,
        output_dir: Path | None,
        resolution: str,
        video_format: str,
        audio_format: str,
        browser_cookies: str | None = None,
    ) -> None:
        console.print("⏳ Fetching media info...")
        try:
            info = extract_info(url, browser_cookies=browser_cookies)
        except Exception as exc:
            if self._should_offer_cookies(str(exc)) and not browser_cookies:
                cookie_browser = select_browser_cookies()
                if cookie_browser and cookie_browser != "none":
                    return self._download_single(
                        url=url,
                        download_type=download_type,
                        output_dir=output_dir,
                        resolution=resolution,
                        video_format=video_format,
                        audio_format=audio_format,
                        browser_cookies=cookie_browser,
                    )
            console.print(f"[red]✗ Error:[/red] Failed to fetch info: {exc}")
            return

        title = info.get("title", "Unknown")
        quality = get_best_quality(info, download_type)
        duration = int(info.get("duration", 0) or 0)
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = (
            f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            if hours
            else f"{minutes:02d}:{seconds:02d}"
        )

        console.print(f"📹 Title: [bold]{title}[/bold]")
        console.print(f"🎥 Stream: [cyan]{quality}[/cyan]")
        if duration:
            console.print(f"⏱  Duration: [yellow]{duration_str}[/yellow]")
        console.print(f"🎯 Target Quality: [bold green]{resolution}[/bold green]")

        target_dir = output_dir or Path.home() / "Downloads"
        console.print(f"📁 Saving to: [cyan]{target_dir}[/cyan]")

        try:
            run_download(
                url=url,
                download_type=download_type,
                video_format=video_format,
                audio_format=audio_format,
                resolution=resolution,
                output_dir=target_dir,
                browser_cookies=browser_cookies,
            )
        except Exception as exc:
            if self._should_offer_cookies(str(exc)) and not browser_cookies:
                cookie_browser = select_browser_cookies()
                if cookie_browser and cookie_browser != "none":
                    return self._download_single(
                        url=url,
                        download_type=download_type,
                        output_dir=output_dir,
                        resolution=resolution,
                        video_format=video_format,
                        audio_format=audio_format,
                        browser_cookies=cookie_browser,
                    )
            console.print(f"\n[red]✗ Error:[/red] Download failed: {exc}")
            return

        console.print(f"\n[green]✓ Download complete! Saved to {target_dir}[/green]")

    @staticmethod
    def _should_offer_cookies(error_msg: str) -> bool:
        lowered = error_msg.lower()
        triggers = [
            "sign in",
            "confirm your age",
            "confirm you're not a bot",
            "login required",
            "private video",
            "http error 401",
            "http error 403",
            "cookies",
        ]
        return any(t in lowered for t in triggers)
