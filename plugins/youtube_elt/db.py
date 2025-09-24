"""
MongoDB utility module.
Provides a singleton MongoClient and helper functions for collections and indexes.
"""
from __future__ import annotations

from typing import Optional
import os
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from datetime import datetime, timezone

from config.settings import config

_client: Optional[MongoClient] = None


def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        use_mock = (os.getenv("USE_MOCK_DB", "false").lower() == "true")
        if use_mock:
            import mongomock  # type: ignore
            _client = mongomock.MongoClient()
        else:
            _client = MongoClient(config.mongo_connection_string)
    return _client


def get_db() -> Database:
    return get_mongo_client()[config.MONGO_DATABASE]


def get_collection(name: str) -> Collection:
    return get_db()[name]


def ensure_indexes():
    """Create indexes to enforce uniqueness and improve performance."""
    staging = get_collection(config.STAGING_COLLECTION)
    core = get_collection(config.CORE_COLLECTION)
    history = get_collection(config.HISTORY_COLLECTION)

    staging.create_index([("video_id", ASCENDING)], unique=True, name="ux_staging_video")
    core.create_index([("video_id", ASCENDING)], unique=True, name="ux_core_video")
    history.create_index([("video_id", ASCENDING), ("valid_from", ASCENDING)], name="ix_hist_video_from")


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
