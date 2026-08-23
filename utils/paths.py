from pathlib import Path


def get_downloads_dir() -> Path:
    return Path.home() / "Downloads"


def ensure_downloads_dir() -> Path:
    downloads = get_downloads_dir()
    downloads.mkdir(parents=True, exist_ok=True)
    return downloads


def safe_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    for ch in invalid:
        name = name.replace(ch, "_")
    return name.strip()
