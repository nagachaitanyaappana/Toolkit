from __future__ import annotations

from pathlib import Path

from utils.paths import get_downloads_dir


def build_yt_dlp_options(
    url: str,
    output_dir: Path | None = None,
    video_format: str = "mp4",
    audio_format: str = "mp3",
    download_type: str = "video",
    cookies_file: Path | None = None,
) -> dict:
    out_dir = output_dir or get_downloads_dir()
    out_template = str(out_dir / "%(title)s.%(ext)s")

    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": out_template,
        "concurrent_fragment_downloads": 8,
    }

    if cookies_file and cookies_file.exists():
        opts["cookiefile"] = str(cookies_file)

    if download_type == "audio":
        opts.update(
            {
                "format": "bestaudio",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": audio_format,
                        "preferredquality": "0",
                    }
                ],
            }
        )
    else:
        opts.update(
            {
                "format": f"bestvideo[ext={video_format}]+bestaudio[ext=m4a]/best[ext={video_format}]",
                "merge_output_format": video_format,
            }
        )

    return opts
