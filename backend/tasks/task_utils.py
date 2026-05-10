"""Shared utilities for ingestion tasks."""
import html
import re


def tracker_allows_source(tracker, source: str) -> bool:
    """Return True if this tracker should be fetched from the given source.

    An empty sources list means all sources are enabled (opt-out model).
    """
    return not tracker.sources or source in tracker.sources


def strip_html(text: str) -> str:
    """Strip HTML tags and decode HTML entities. Normalizes whitespace."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
