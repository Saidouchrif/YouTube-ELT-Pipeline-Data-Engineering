"""
Configuration pour le pipeline YouTube ELT
"""
import os
from typing import Dict, Any

# Configuration de l'API YouTube
YOUTUBE_API_CONFIG = {
    "api_key": os.getenv("YOUTUBE_API_KEY", "AIzaSyAr6B9F18e9vrR5_5sp4dDIVulnup3cqXc"),
    "base_url": "https://www.googleapis.com/youtube/v3",
    "daily_quota_limit": 10000,
    "max_videos_per_page": 50,
    "max_videos_per_batch": 50,
    "request_delay": 0.1,  # Délai entre les requêtes en secondes
}

# Configuration de la pagination
PAGINATION_CONFIG = {
    "max_pages_per_request": 20,  # Limite de pages par requête
    "default_max_results": 50,
    "max_results_limit": 1000,  # Limite absolue de vidéos par requête
}

# Configuration des quotas
QUOTA_CONFIG = {
    "costs": {
        "channels": 1,
        "playlistItems": 1,
        "videos": 1,
        "search": 100,
        "commentThreads": 1,
        "comments": 1
    },
    "quota_file": "quota_usage.json",
    "reset_hour": 0,  # Heure de remise à zéro (UTC)
}

# Configuration du logging
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "youtube_elt.log"
}

# Configuration des données extraites
DATA_CONFIG = {
    "max_description_length": 500,
    "max_tags_count": 10,
    "thumbnail_size": "medium",  # small, medium, high, standard, maxres
    "include_private_videos": False,
}

def get_config() -> Dict[str, Any]:
    """Retourne la configuration complète"""
    return {
        "youtube_api": YOUTUBE_API_CONFIG,
        "pagination": PAGINATION_CONFIG,
        "quota": QUOTA_CONFIG,
        "logging": LOGGING_CONFIG,
        "data": DATA_CONFIG
    }
