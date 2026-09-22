from __future__ import annotations

from pathlib import Path

from utils.paths import get_downloads_dir


def build_yt_dlp_options(
    url: str,
    output_dir: Path | str | None = None,
    video_format: str = "mp4",
    audio_format: str = "mp3",
    download_type: str = "video",
    resolution: str = "best",
    is_playlist: bool = False,
    cookies_file: Path | None = None,
    browser_cookies: str | None = None,
) -> dict:
    out_dir = Path(output_dir) if output_dir else get_downloads_dir()
    if is_playlist:
        out_template = str(out_dir / "%(playlist_index)02d - %(title)s.%(ext)s")
    else:
        out_template = str(out_dir / "%(title)s.%(ext)s")

    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": out_template,
        "concurrent_fragment_downloads": 8,
        "windowsfilenames": True,
    }

    if cookies_file and cookies_file.exists():
        opts["cookiefile"] = str(cookies_file)
    elif browser_cookies:
        opts["cookiesfrombrowser"] = (browser_cookies,)

    if download_type == "audio":
        opts.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": audio_format,
                        "preferredquality": "320" if audio_format == "mp3" else "0",
                    }
                ],
            }
        )
    else:
        if resolution in ("best", "", None):
            fmt = "bestvideo*+bestaudio/best"
        else:
            fmt = f"bestvideo*[height<={resolution}]+bestaudio/best[height<={resolution}]/best"

        opts.update(
            {
                "format": fmt,
                "merge_output_format": video_format,
            }
        )

    return opts
