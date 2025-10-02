"""
MongoDB Loading Module for YouTube ELT Pipeline.

Functions:
- load_staging_from_file: Load raw JSON into staging collection.
- transform_and_upsert_core: Transform records and upsert into core collection.
- upsert_history: Maintain history SCD2 style with valid_from/valid_to.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

from pymongo import UpdateOne

from config.settings import config
from youtube_elt.db import get_collection, ensure_indexes, utcnow_iso
from youtube_elt.transform import transform_dataset


def load_staging_from_file(file_path: str) -> int:
    """Load a JSON file produced by extraction into staging collection.

    Returns number of inserted/updated records.
    """
    ensure_indexes()
    staging = get_collection(config.STAGING_COLLECTION)

    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Staging file not found: {file_path}")

    with p.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    videos: List[Dict[str, Any]] = payload.get("videos", [])
    ops: List[UpdateOne] = []
    for v in videos:
        v["_ingested_at"] = utcnow_iso()
        ops.append(
            UpdateOne({"video_id": v.get("video_id")}, {"$set": v}, upsert=True)
        )

    if not ops:
        return 0

    res = staging.bulk_write(ops, ordered=False)
    return (res.upserted_count or 0) + (res.modified_count or 0)


def transform_and_upsert_core(dataset: Dict[str, Any]) -> int:
    """Transform extracted dataset and upsert to core collection."""
    ensure_indexes()
    core = get_collection(config.CORE_COLLECTION)

    transformed = transform_dataset(dataset)
    videos = transformed.get("videos", [])

    ops: List[UpdateOne] = []
    now = utcnow_iso()
    for v in videos:
        v["updated_at"] = now
        # Remove created_at from the document to avoid conflict
        v_copy = v.copy()
        v_copy.pop("created_at", None)
        
        ops.append(
            UpdateOne(
                {"video_id": v["video_id"]},
                {"$set": v_copy, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        )

    if not ops:
        return 0

    res = core.bulk_write(ops, ordered=False)
    return (res.upserted_count or 0) + (res.modified_count or 0)


def upsert_history(dataset: Dict[str, Any]) -> int:
    """
    Maintain history SCD2-like in history collection.

    Strategy:
    - For each video, close current open record (valid_to null) if any field changed.
    - Insert a new record snapshot with valid_from=now, valid_to=null.
    """
    ensure_indexes()
    history = get_collection(config.HISTORY_COLLECTION)

    videos = transform_dataset(dataset).get("videos", [])
    now = utcnow_iso()
    count = 0

    for v in videos:
        vid = v["video_id"]
        # fetch latest open record
        current = history.find_one({"video_id": vid, "valid_to": {"$in": [None, ""]}}, sort=[("valid_from", -1)])

        if current:
            # compare significant fields
            fields = [
                "title",
                "description",
                "duration_seconds",
                "view_count",
                "like_count",
                "comment_count",
                "thumbnail_url",
                "content_type",
            ]
            changed = any(current.get(f) != v.get(f) for f in fields)
            if changed:
                history.update_one({"_id": current["_id"]}, {"$set": {"valid_to": now, "updated_at": now}})
                v.update({"valid_from": now, "valid_to": None, "created_at": now, "updated_at": now})
                history.insert_one(v)
                count += 1
        else:
            v.update({"valid_from": now, "valid_to": None, "created_at": now, "updated_at": now})
            history.insert_one(v)
            count += 1

    return count
