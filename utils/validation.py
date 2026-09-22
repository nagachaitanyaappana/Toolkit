import re
from urllib.parse import urlparse

URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def is_valid_url(url: str) -> bool:
    if not isinstance(url, str) or not url.strip():
        return False
    url = url.strip()
    if not URL_RE.match(url):
        return False
    try:
        result = urlparse(url)
        return bool(result.scheme and result.netloc)
    except Exception:
        return False


def looks_like_media_url(url: str) -> bool:
    if not is_valid_url(url):
        return False
    lowered = url.lower()
    return any(
        domain in lowered
        for domain in [
            "youtube.com",
            "youtu.be",
            "instagram.com",
            "open.spotify.com",
            "pinterest.com",
            "pin.it",
            "reddit.com",
            "x.com",
            "twitter.com",
            "soundcloud.com",
            "bandcamp.com",
        ]
    )
