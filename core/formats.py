from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Format:
    format_id: str
    extension: str
    resolution: str
    note: str
    filesize: int | None


@dataclass
class MediaInfo:
    title: str
    uploader: str
    thumbnail: str
    duration: float
    video_formats: list[Format]
    audio_formats: list[Format]
