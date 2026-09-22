from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yt_dlp

from core.formats import MediaInfo, Format
from core.options import build_yt_dlp_options


def check_ffmpeg() -> bool:
    """Return True if ffmpeg is found in PATH."""
    return shutil.which("ffmpeg") is not None


def is_spotify_url(url: str) -> bool:
    """Check if the given URL is a Spotify link."""
    return "open.spotify.com" in url or "spotify.link" in url


def get_spotify_type(url: str) -> str:
    """Detect whether a Spotify URL is a track, album, playlist, or artist."""
    url_lower = url.lower()
    if "/track/" in url_lower:
        return "track"
    elif "/album/" in url_lower:
        return "album"
    elif "/playlist/" in url_lower:
        return "playlist"
    elif "/artist/" in url_lower:
        return "artist"
    return "unknown"


def is_spotify_playlist(url: str) -> bool:
    """Backward compatibility check for Spotify playlists or albums."""
    return is_spotify_url(url) and get_spotify_type(url) in ("playlist", "album")


def has_mixed_video_and_playlist(url: str) -> bool:
    """Detect if URL has both a specific video ID and a playlist ID (e.g. YouTube watch?v=...&list=...)."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    has_video = "v" in qs or "watch" in parsed.path or "youtu.be" in parsed.netloc
    has_list = "list" in qs
    return bool(has_video and has_list)


def strip_playlist_params(url: str) -> str:
    """Remove list= and index= query parameters so only the single video is processed."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    qs.pop("list", None)
    qs.pop("index", None)
    flat_query = "&".join(f"{k}={v[0]}" for k, v in qs.items())
    return parsed._replace(query=flat_query).geturl()


def is_playlist(url: str) -> bool:
    """Detect if URL points directly to a playlist/album."""
    if is_spotify_url(url):
        return get_spotify_type(url) in ("playlist", "album")
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "list" in qs and not ("v" in qs or "watch" in parsed.path):
        return True
    if "/playlist" in parsed.path or "/sets/" in parsed.path:
        return True
    return False


def extract_info(
    url: str,
    cookies_file: Path | None = None,
    browser_cookies: str | None = None,
) -> dict:
    ydl_opts: dict = {"quiet": True, "no_warnings": True, "extract_flat": False}
    if cookies_file and cookies_file.exists():
        ydl_opts["cookiefile"] = str(cookies_file)
    elif browser_cookies:
        ydl_opts["cookiesfrombrowser"] = (browser_cookies,)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def extract_playlist_info(
    url: str,
    cookies_file: Path | None = None,
    browser_cookies: str | None = None,
) -> dict:
    ydl_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }
    if cookies_file and cookies_file.exists():
        ydl_opts["cookiefile"] = str(cookies_file)
    elif browser_cookies:
        ydl_opts["cookiesfrombrowser"] = (browser_cookies,)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def parse_range(range_str: str, max_num: int) -> list[int]:
    indices = set()
    for part in range_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start = max(1, int(start.strip()))
            end = min(max_num, int(end.strip()))
            indices.update(range(start, end + 1))
        else:
            try:
                num = int(part)
                if 1 <= num <= max_num:
                    indices.add(num)
            except ValueError:
                pass
    return sorted(indices)


def build_media_info(info: dict) -> MediaInfo:
    video_formats: list[Format] = []
    audio_formats: list[Format] = []

    for fmt in info.get("formats", []):
        if fmt.get("vcodec") != "none" and fmt.get("acodec") != "none":
            video_formats.append(
                Format(
                    format_id=fmt.get("format_id", ""),
                    extension=fmt.get("ext", ""),
                    resolution=fmt.get("resolution", "unknown"),
                    note=fmt.get("format_note", ""),
                    filesize=fmt.get("filesize") or fmt.get("filesize_approx"),
                )
            )
        elif fmt.get("vcodec") == "none" and fmt.get("acodec") != "none":
            audio_formats.append(
                Format(
                    format_id=fmt.get("format_id", ""),
                    extension=fmt.get("ext", ""),
                    resolution=fmt.get("acodec", "audio"),
                    note=fmt.get("format_note", ""),
                    filesize=fmt.get("filesize") or fmt.get("filesize_approx"),
                )
            )

    unique_videos: list[Format] = []
    seen = set()
    for fmt in video_formats:
        key = (fmt.resolution, fmt.extension)
        if key not in seen:
            seen.add(key)
            unique_videos.append(fmt)

    unique_audios: list[Format] = []
    seen = set()
    for fmt in audio_formats:
        key = (fmt.extension,)
        if key not in seen:
            seen.add(key)
            unique_audios.append(fmt)

    return MediaInfo(
        title=info.get("title", "Unknown"),
        uploader=info.get("uploader", "Unknown"),
        thumbnail=info.get("thumbnail", ""),
        duration=info.get("duration", 0.0),
        video_formats=unique_videos,
        audio_formats=unique_audios,
    )


def format_filesize(size: int | float | str | None) -> str:
    if not size:
        return "Unknown"
    try:
        size = float(size)
    except (ValueError, TypeError):
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def get_best_quality(info: dict, download_type: str) -> str:
    if download_type == "audio":
        formats = [f for f in info.get("formats", []) if f.get("vcodec") == "none" and f.get("acodec") != "none"]
        if formats:
            best = max(formats, key=lambda f: f.get("abr") or 0)
            abr = best.get("abr", "?")
            ext = best.get("ext", "?")
            return f"{ext.upper()} @ {abr}kbps"
        return "Best audio"
    else:
        formats = [f for f in info.get("formats", []) if f.get("vcodec") != "none"]
        if formats:
            best = max(formats, key=lambda f: f.get("height") or 0)
            res = best.get("resolution", "?")
            ext = best.get("ext", "?")
            fps = best.get("fps", "")
            fps_str = f" {fps}fps" if fps else ""
            return f"{res}{fps_str} ({ext.upper()})"
        return "Best video"


def run_download(
    url: str,
    download_type: str,
    video_format: str = "mp4",
    audio_format: str = "mp3",
    resolution: str = "best",
    output_dir: Path | None = None,
    cookies_file: Path | None = None,
    browser_cookies: str | None = None,
) -> None:
    opts = build_yt_dlp_options(
        url=url,
        output_dir=output_dir,
        video_format=video_format,
        audio_format=audio_format,
        download_type=download_type,
        resolution=resolution,
        is_playlist=False,
        cookies_file=cookies_file,
        browser_cookies=browser_cookies,
    )

    def _hook(d: dict) -> None:
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed else "--"
            if total:
                percent = downloaded * 100 / total
                bar_len = 30
                filled = int(bar_len * downloaded / total)
                bar = "█" * filled + "░" * (bar_len - filled)
                sys.stdout.write(f"\r⬇ [{bar}] {percent:5.1f}% | {format_filesize(downloaded)}/{format_filesize(total)} | {speed_str}")
            else:
                sys.stdout.write(f"\r⬇ {format_filesize(downloaded)} downloaded | {speed_str}")
            sys.stdout.flush()
        elif status == "finished":
            sys.stdout.write("\n⚙️  Processing / Merging with FFmpeg...\n")
            sys.stdout.flush()

    opts["progress_hooks"] = [_hook]
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


def run_download_playlist(
    entries: list[dict],
    download_type: str,
    output_dir: Path,
    video_format: str = "mp4",
    audio_format: str = "mp3",
    resolution: str = "best",
    cookies_file: Path | None = None,
    browser_cookies: str | None = None,
) -> None:
    total = len(entries)
    for idx, entry in enumerate(entries, 1):
        url = entry.get("url") or entry.get("webpage_url")
        if not url:
            continue
        title = entry.get("title", "Unknown")
        sys.stdout.write(f"\n📹 [{idx}/{total}]: {title}\n")
        sys.stdout.flush()

        opts = build_yt_dlp_options(
            url=url,
            output_dir=output_dir,
            video_format=video_format,
            audio_format=audio_format,
            download_type=download_type,
            resolution=resolution,
            is_playlist=True,
            cookies_file=cookies_file,
            browser_cookies=browser_cookies,
        )

        def _hook(d: dict, current=idx, total_videos=total) -> None:
            status = d.get("status")
            if status == "downloading":
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                speed = d.get("speed") or 0
                speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed else "--"
                if total_bytes:
                    percent = downloaded * 100 / total_bytes
                    bar_len = 25
                    filled = int(bar_len * downloaded / total_bytes)
                    bar = "█" * filled + "░" * (bar_len - filled)
                    sys.stdout.write(
                        f"\r⬇ [{current}/{total_videos}] [{bar}] {percent:5.1f}% | "
                        f"{format_filesize(downloaded)}/{format_filesize(total_bytes)} | {speed_str}"
                    )
                else:
                    sys.stdout.write(f"\r⬇ [{current}/{total_videos}] {format_filesize(downloaded)} downloaded | {speed_str}")
                sys.stdout.flush()
            elif status == "finished":
                sys.stdout.write(f"\r⬇ [{current}/{total_videos}] ⚙️  Processing / Finalizing...\n")
                sys.stdout.flush()

        opts["progress_hooks"] = [_hook]
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
