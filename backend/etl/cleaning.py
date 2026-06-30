from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import urlparse, urlunparse


def clean_text(raw_text: str | None) -> str | None:
    """Normalize whitespace, strip HTML, and unescape entities."""
    if raw_text is None:
        return None

    text = html.unescape(raw_text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip() or None


def normalize_url(url: str | None) -> str | None:
    """Normalize Reddit URLs to a canonical form for deduplication."""
    if not url:
        return None

    try:
        parsed = urlparse(url.strip())
        normalized_path = parsed.path.rstrip("/")
        normalized = urlunparse(
            (
                parsed.scheme or "https",
                parsed.netloc.lower(),
                normalized_path,
                "",
                "",
                "",
            )
        )
        return normalized
    except Exception:
        return url.strip()


def normalize_author(author: str | None) -> str | None:
    """Normalize author labels, returning None for empty values."""
    if not author:
        return None
    cleaned = clean_text(author)
    return cleaned if cleaned and cleaned.lower() != "[deleted]" else None


def make_safe_int(value: Any, default: int = 0) -> int:
    """Convert a numeric value to int or return a safe default."""
    try:
        return int(value)
    except Exception:
        return default
