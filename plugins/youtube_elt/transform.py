"""
Data Transformation Module for YouTube ELT Pipeline.

- Convert ISO 8601 durations to seconds.
- Normalize and standardize field names and types.
- Parse timestamps to ISO format.
- Classify content type (e.g. short, longform, livestream replay) based on heuristics.
"""

from __future__ import annotations

import datetime
from typing import Dict, Any, List

import isodate


def iso8601_duration_to_seconds(duration_str: str) -> int:
    """Convert ISO 8601 duration (e.g. PT1H2M10S) to total seconds."""
    try:
        duration = isodate.parse_duration(duration_str)
        return int(duration.total_seconds())
    except Exception:
        return 0


def parse_published_at(ts: str) -> str:
    """Normalize published_at to ISO 8601 Z format."""
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return ts


def classify_content(video: Dict[str, Any]) -> str:
    """Simple heuristic to classify content type."""
    title = (video.get("title") or "").lower()
    duration_sec = video.get("duration_seconds") or 0

    if "live" in title or "premiere" in title:
        # heuristic only; true live info requires a separate API part
        return "live_or_premiere"

    if "#short" in title or duration_sec < 60:
        return "short"

    if duration_sec >= 1200:  # >= 20 minutes
        return "longform"

    return "standard"


def standardize_video(video: Dict[str, Any]) -> Dict[str, Any]:
    """Standardize a single video record to the core schema."""
    duration_seconds = iso8601_duration_to_seconds(video.get("duration", ""))
    published_at = parse_published_at(video.get("published_at", ""))

    std = {
        "video_id": video.get("video_id"),
        "title": video.get("title", "").strip(),
        "description": video.get("description", ""),
        "published_at": published_at,
        "duration_seconds": duration_seconds,
        "view_count": int(video.get("view_count", 0) or 0),
        "like_count": int(video.get("like_count", 0) or 0),
        "comment_count": int(video.get("comment_count", 0) or 0),
        "thumbnail_url": video.get("thumbnail_url", ""),
        "channel_id": video.get("channel_id", ""),
        "channel_title": video.get("channel_title", ""),
        "tags": video.get("tags", []) or [],
        "category_id": str(video.get("category_id", "")),
        "default_language": video.get("default_language", ""),
        "default_audio_language": video.get("default_audio_language", ""),
    }
    std["content_type"] = classify_content(std)
    return std


def transform_dataset(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform the full extracted dataset into the standardized core schema.
    """
    videos = dataset.get("videos", [])
    transformed = [standardize_video(v) for v in videos]

    return {
        "channel_handle": dataset.get("channel_handle"),
        "extraction_date": dataset.get("extraction_date"),
        "total_videos": len(transformed),
        "videos": transformed,
    }
