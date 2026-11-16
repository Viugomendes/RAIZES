"""Interview videos hosted on YouTube.

The admin accepts the normal link of the video; the site extracts the video
code and builds the player address by itself.
"""
import re
from urllib.parse import parse_qs, urlsplit

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_WATCH_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}
_SHORT_HOSTS = {"youtu.be", "www.youtu.be"}


def extract_video_id(url: str) -> str | None:
    """Return the video code of a `youtube.com/watch?v=` or `youtu.be/` link.

    Any other address returns None.
    """
    try:
        parts = urlsplit((url or "").strip())
    except ValueError:
        return None
    if parts.scheme not in ("http", "https"):
        return None
    host = (parts.hostname or "").lower()
    if host in _WATCH_HOSTS and parts.path == "/watch":
        candidate = parse_qs(parts.query).get("v", [""])[0]
    elif host in _SHORT_HOSTS:
        candidate = parts.path.strip("/")
    else:
        return None
    return candidate if _VIDEO_ID.match(candidate) else None


def embed_url(video_id: str) -> str:
    """Address of the player shown inside the page, on the no-cookies domain."""
    return f"https://www.youtube-nocookie.com/embed/{video_id}"


def watch_url(video_id: str, start: int | None = None) -> str:
    """Address of the video on YouTube, optionally starting at a given second."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    if start:
        url += f"&t={start}s"
    return url
