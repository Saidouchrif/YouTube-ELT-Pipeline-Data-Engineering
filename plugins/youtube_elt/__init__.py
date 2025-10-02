"""
YouTube ELT Plugin Package.

This package provides extraction, transformation, and loading functionality
for YouTube data using the YouTube Data API v3.
"""

from youtube_elt.extract import YouTubeExtractor, extract_youtube_data
from youtube_elt.transform import transform_dataset, standardize_video
from youtube_elt.load import load_staging_from_file, transform_and_upsert_core, upsert_history
from youtube_elt.db import get_collection, ensure_indexes, utcnow_iso

__all__ = [
    'YouTubeExtractor',
    'extract_youtube_data',
    'transform_dataset',
    'standardize_video',
    'load_staging_from_file',
    'transform_and_upsert_core',
    'upsert_history',
    'get_collection',
    'ensure_indexes',
    'utcnow_iso'
]
