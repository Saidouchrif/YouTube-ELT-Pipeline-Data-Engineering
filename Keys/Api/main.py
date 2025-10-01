from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import datetime
import sys
import os
import json
import logging
from typing import Optional

# Ajouter le répertoire parent au path pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quota_manager import QuotaManager
from pagination_manager import PaginationManager
from data_saver import DataSaver
from Api.mongodb_handler import MongoDBHandler

app = FastAPI(title="YouTube ELT Pipeline API", version="2.0.0")

API_KEY = "AIzaSyAr6B9F18e9vrR5_5sp4dDIVulnup3cqXc"  # Mettre ici votre clé API

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialiser les gestionnaires
quota_manager = QuotaManager()
pagination_manager = PaginationManager(API_KEY, quota_manager)
data_saver = DataSaver()
mongodb_handler = MongoDBHandler()


# ======================
# Modèle de données pour la requête POST
# ======================
class ChannelRequest(BaseModel):
    channel_handle: str       # Identifiant ou pseudo de la chaîne YouTube
    max_results: int = 5      # Nombre maximum de vidéos à récupérer (valeur par défaut)
    use_pagination: bool = True  # Utiliser la pagination pour récupérer plus de vidéos
    save_to_file: bool = True    # Sauvegarder automatiquement en fichier JSON
    save_to_mongodb: bool = True  # Sauvegarder dans MongoDB


# ======================
# Fonction utilitaire pour récupérer les vidéos d'une chaîne (version legacy)
# ======================
def fetch_channel_videos_legacy(channel_handle: str, max_results: int = 5):
    """Version legacy sans gestion des quotas et pagination"""
    # 1. Récupérer le playlistId de la playlist "uploads" de la chaîne
    url_channel = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&forHandle={channel_handle}&key={API_KEY}"
    response_channel = requests.get(url_channel).json()
    uploads_playlist_id = response_channel["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # 2. Récupérer les dernières vidéos de cette playlist
    url_playlist = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId={uploads_playlist_id}&maxResults={max_results}&key={API_KEY}"
    response_playlist = requests.get(url_playlist).json()
    video_ids = [item["contentDetails"]["videoId"] for item in response_playlist["items"]]

    # 3. Récupérer les détails et statistiques des vidéos
    video_ids_str = ",".join(video_ids)
    url_videos = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails,statistics&id={video_ids_str}&key={API_KEY}"
    response_videos = requests.get(url_videos).json()

    # 4. Construire le JSON final
    data = {
        "channel_handle": channel_handle,
        "extraction_date": datetime.datetime.utcnow().isoformat(),
        "total_videos": len(response_videos["items"]),
        "videos": []
    }

    for item in response_videos["items"]:
        video = {
            "title": item["snippet"]["title"],                          # Titre de la vidéo
            "duration": item["contentDetails"]["duration"],            # Durée en format ISO 8601
            "video_id": item["id"],                                    # ID de la vidéo
            "like_count": item["statistics"].get("likeCount", "0"),    # Nombre de "likes"
            "view_count": item["statistics"].get("viewCount", "0"),    # Nombre de vues
            "published_at": item["snippet"]["publishedAt"],           # Date de publication
            "comment_count": item["statistics"].get("commentCount", "0")  # Nombre de commentaires
        }
        data["videos"].append(video)

    return data


# ======================
# Endpoints API
# ======================

@app.get("/")
def root():
    """Endpoint racine avec informations sur l'API"""
    return {
        "message": "YouTube ELT Pipeline API v2.0",
        "features": [
            "Gestion des quotas API (10,000 unités/jour)",
            "Pagination automatique",
            "Suivi des quotas en temps réel",
            "Récupération optimisée des vidéos"
        ],
        "endpoints": {
            "/channel": "POST - Récupérer les données d'une chaîne",
            "/quota/status": "GET - Statut des quotas",
            "/quota/estimate": "GET - Estimation du coût d'une requête",
            "/data/extractions": "GET - Liste des extractions sauvegardées",
            "/data/stats": "GET - Statistiques des données sauvegardées"
        }
    }

@app.get("/quota/status")
def get_quota_status():
    """Récupère le statut actuel des quotas API"""
    return quota_manager.get_quota_status()

@app.get("/quota/estimate")
def estimate_quota_cost(channel_handle: str, max_results: int = 50):
    """
    Estime le coût en quota pour récupérer des vidéos d'une chaîne
    
    Args:
        channel_handle: Handle de la chaîne YouTube
        max_results: Nombre de vidéos à récupérer
    """
    # Coût estimé: 1 (channels) + pages (playlistItems) + batches (videos)
    pages_needed = (max_results + 49) // 50  # 50 vidéos par page max
    batches_needed = (max_results + 49) // 50  # 50 vidéos par batch max
    
    total_cost = 1 + pages_needed + batches_needed
    
    return {
        "channel_handle": channel_handle,
        "max_results": max_results,
        "estimated_cost": total_cost,
        "breakdown": {
            "channels_call": 1,
            "playlist_items_calls": pages_needed,
            "videos_calls": batches_needed
        },
        "quota_available": quota_manager.check_quota_available('videos', total_cost),
        "current_quota_status": quota_manager.get_quota_status()
    }

@app.post("/channel")
def get_channel_data(request: ChannelRequest):
    """
    🔹 Endpoint POST pour récupérer les données d'une chaîne YouTube avec gestion des quotas et pagination
    
    - Body JSON attendu :
      {
        "channel_handle": "MrBeast",
        "max_results": 50,
        "use_pagination": true
      }
    """
    try:
        # Vérifier les limites de quota
        if not quota_manager.can_fetch_videos(request.max_results):
            quota_status = quota_manager.get_quota_status()
            raise HTTPException(
                status_code=429, 
                detail={
                    "error": "Quota insuffisant",
                    "message": f"Impossible de récupérer {request.max_results} vidéos avec le quota restant",
                    "quota_status": quota_status,
                    "suggestion": f"Essayez avec {quota_manager.get_max_videos_possible()} vidéos maximum"
                }
            )
        
        # Utiliser la nouvelle méthode avec pagination et gestion des quotas
        if request.use_pagination:
            result = pagination_manager.fetch_channel_videos_complete(
                request.channel_handle, 
                request.max_results
            )
            
            # Vérifier s'il y a eu une erreur
            if "error" in result:
                raise HTTPException(status_code=400, detail=result)
        else:
            # Utiliser la méthode legacy pour compatibilité
            result = fetch_channel_videos_legacy(request.channel_handle, request.max_results)
        
        # Sauvegarder en fichier JSON si demandé
        if request.save_to_file and not ("error" in result):
            try:
                saved_files = data_saver.save_channel_data(result, request.channel_handle)
                result["_saved_files"] = saved_files
                result["_saved_at"] = datetime.datetime.utcnow().isoformat()
            except Exception as e:
                logger.warning(f"Erreur lors de la sauvegarde: {e}")
                result["_save_error"] = str(e)
        
        # Sauvegarder dans MongoDB si demandé
        if request.save_to_mongodb and not ("error" in result):
            try:
                # Sauvegarder les données brutes dans staging_data
                staging_result = mongodb_handler.save_to_staging(result)
                if staging_result:
                    result["_mongodb_staging"] = staging_result
                    logger.info(f"Données sauvegardées dans staging_data: {staging_result['inserted_id']}")
                
                # Sauvegarder les vidéos individuelles dans core_data
                if "videos" in result and result["videos"]:
                    core_result = mongodb_handler.save_videos_to_core(result["videos"], request.channel_handle)
                    if core_result:
                        result["_mongodb_core"] = core_result
                        logger.info(f"Vidéos sauvegardées dans core_data: {core_result['upserted_count']}")
                    
                    # Sauvegarder aussi dans history_data pour l'historisation
                    history_result = mongodb_handler.save_videos_to_history(result["videos"], request.channel_handle)
                    if history_result:
                        result["_mongodb_history"] = history_result
                        logger.info(f"Vidéos sauvegardées dans history_data: {history_result['inserted_count']}")
                
            except Exception as e:
                logger.warning(f"Erreur lors de la sauvegarde MongoDB: {e}")
                result["_mongodb_error"] = str(e)
        
        return result
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.post("/channel/legacy")
def get_channel_data_legacy(request: ChannelRequest):
    """
    🔹 Endpoint POST legacy pour compatibilité (sans gestion des quotas)
    """
    return fetch_channel_videos_legacy(request.channel_handle, request.max_results)

@app.get("/data/extractions")
def get_extractions_list(channel_handle: Optional[str] = None, date: Optional[str] = None):
    """
    🔹 Récupère la liste des extractions sauvegardées
    
    Args:
        channel_handle: Filtrer par chaîne spécifique (optionnel)
        date: Filtrer par date au format YYYYMMDD (optionnel)
    """
    try:
        if channel_handle:
            # Extractions pour une chaîne spécifique
            extractions = data_saver.get_channel_extractions(channel_handle)
            return {
                "channel_handle": channel_handle,
                "extractions_count": len(extractions),
                "extractions": extractions
            }
        elif date:
            # Extractions pour une date spécifique
            extractions = data_saver.get_daily_extractions(date)
            return {
                "date": date,
                "extractions_count": len(extractions),
                "extractions": extractions
            }
        else:
            # Toutes les extractions
            stats = data_saver.get_extraction_stats()
            return {
                "message": "Liste de toutes les extractions",
                "stats": stats
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des extractions: {str(e)}")

@app.get("/data/stats")
def get_data_stats():
    """
    🔹 Récupère les statistiques globales des données sauvegardées
    """
    try:
        stats = data_saver.get_extraction_stats()
        return {
            "message": "Statistiques des données sauvegardées",
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des statistiques: {str(e)}")

@app.get("/data/channel/{channel_handle}")
def get_channel_data_history(channel_handle: str):
    """
    🔹 Récupère l'historique complet des extractions pour une chaîne
    
    Args:
        channel_handle: Handle de la chaîne YouTube
    """
    try:
        extractions = data_saver.get_channel_extractions(channel_handle)
        
        # Charger les métadonnées de la chaîne
        metadata_file = data_saver.base_data_dir / "metadata" / f"{channel_handle.lower()}_metadata.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        return {
            "channel_handle": channel_handle,
            "extractions_count": len(extractions),
            "extractions": extractions,
            "metadata": metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération de l'historique: {str(e)}")


@app.get("/mongodb/stats")
def get_mongodb_stats():
    """Récupère les statistiques des collections MongoDB"""
    try:
        stats = mongodb_handler.get_collection_stats()
        return {
            "mongodb_connected": mongodb_handler.is_connected(),
            "collections": stats,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur MongoDB: {str(e)}")

@app.get("/mongodb/videos/{channel_handle}")
def get_mongodb_videos(channel_handle: str, limit: int = 10):
    """Récupère les vidéos d'une chaîne depuis MongoDB"""
    try:
        videos = mongodb_handler.get_recent_videos(channel_handle, limit)
        return {
            "channel_handle": channel_handle,
            "videos_count": len(videos),
            "videos": videos,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur MongoDB: {str(e)}")

@app.get("/health")
def health_check():
    """Endpoint de santé pour vérifier que l'API fonctionne"""
    mongodb_status = mongodb_handler.is_connected() if mongodb_handler else False
    return {
        "status": "healthy", 
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "service": "YouTube ELT Pipeline API",
        "version": "2.0.0",
        "mongodb_connected": mongodb_status
    }
