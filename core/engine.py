from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yt_dlp

from core.formats import MediaInfo, Format
from core.options import build_yt_dlp_options


def extract_info(url: str, cookies_file: Path | None = None) -> dict:
    ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": False}
    if cookies_file and cookies_file.exists():
        ydl_opts["cookiefile"] = str(cookies_file)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def is_spotify_playlist(url: str) -> bool:
    return "open.spotify.com" in url and "/playlist/" in url


def is_playlist(url: str) -> bool:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    return "list" in qs


def extract_spotify_playlist(url: str) -> dict:
    import subprocess

    result = subprocess.run(
        ["spotdl", "save", url, "--save-file", "/tmp/vdown_spotify.spotdl"],
        capture_output=True,
        text=True,
        timeout=1200,
    )

    import json
    import os

    try:
        with open("/tmp/vdown_spotify.spotdl") as f:
            data = json.load(f)
        os.unlink("/tmp/vdown_spotify.spotdl")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Failed to fetch Spotify playlist: {e}\nspotdl stderr: {result.stderr[:500]}")

    entries = []
    for song in data:
        title = song.get("name", "")
        artists = ", ".join(a.get("name", "") for a in song.get("artists", []))
        entries.append({
            "title": title,
            "artist": artists,
            "uploader": artists,
        })

    playlist_title = data[0].get("album", {}).get("name", "Spotify Playlist") if data else "Spotify Playlist"

    return {
        "title": playlist_title,
        "entries": entries,
    }


def download_spotify_playlist(
    entries: list[dict],
    output_dir: Path,
    audio_format: str = "mp3",
) -> None:
    total = len(entries)
    output_dir.mkdir(parents=True, exist_ok=True)

    for idx, entry in enumerate(entries, 1):
        title = entry.get("title", "Unknown")
        artist = entry.get("artist", entry.get("uploader", ""))
        search_query = f"{artist} {title}".strip()
        sys.stdout.write(f"\n🎵 Track {idx}/{total}: {search_query}\n")
        sys.stdout.flush()

        try:
            result = subprocess.run(
                [
                    "spotdl", "download", search_query,
                    "--output", str(output_dir),
                    "--format", audio_format,
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                sys.stdout.write(f"  ✓ Downloaded\n")
            else:
                sys.stdout.write(f"  ✗ Failed\n")
        except subprocess.TimeoutExpired:
            sys.stdout.write(f"  ✗ Timed out\n")
        except Exception as exc:
            sys.stdout.write(f"  ✗ Error: {exc}\n")
        sys.stdout.flush()


def extract_playlist_info(url: str, cookies_file: Path | None = None) -> dict:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }
    if cookies_file and cookies_file.exists():
        ydl_opts["cookiefile"] = str(cookies_file)
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
            num = int(part)
            if 1 <= num <= max_num:
                indices.add(num)
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
        formats = [f for f in info.get("formats", []) if f.get("vcodec") != "none" and f.get("acodec") == "none"]
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
    output_dir: Path | None = None,
    cookies_file: Path | None = None,
) -> None:
    opts = build_yt_dlp_options(
        url=url,
        output_dir=output_dir,
        video_format=video_format,
        audio_format=audio_format,
        download_type=download_type,
        cookies_file=cookies_file,
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
            sys.stdout.write("\n✓ Finalizing...\n")
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
    cookies_file: Path | None = None,
) -> None:
    total = len(entries)
    for idx, entry in enumerate(entries, 1):
        url = entry.get("url") or entry.get("webpage_url")
        if not url:
            continue
        title = entry.get("title", "Unknown")
        sys.stdout.write(f"\n📹 Video {idx}/{total}: {title}\n")
        sys.stdout.flush()

        opts = build_yt_dlp_options(
            url=url,
            output_dir=output_dir,
            video_format=video_format,
            audio_format=audio_format,
            download_type=download_type,
            cookies_file=cookies_file,
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
                sys.stdout.write(f"\r⬇ [{current}/{total_videos}] ✓ Finalizing...\n")
                sys.stdout.flush()

        opts["progress_hooks"] = [_hook]
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
