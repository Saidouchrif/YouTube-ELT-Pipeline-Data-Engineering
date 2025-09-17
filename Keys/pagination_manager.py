import requests
import time
from typing import List, Dict, Optional, Tuple
import logging
from quota_manager import QuotaManager

logger = logging.getLogger(__name__)

class PaginationManager:
    """
    Gestionnaire de pagination pour l'API YouTube Data v3
    - Gestion automatique des pages suivantes
    - Respect des quotas API
    - Récupération optimisée des vidéos
    """
    
    def __init__(self, api_key: str, quota_manager: QuotaManager):
        self.api_key = api_key
        self.quota_manager = quota_manager
        self.max_videos_per_page = 50  # Limite maximale de l'API YouTube
    
    def fetch_channel_uploads_playlist_id(self, channel_handle: str) -> Optional[str]:
        """
        Récupère l'ID de la playlist des uploads d'une chaîne
        
        Args:
            channel_handle: Handle de la chaîne YouTube
            
        Returns:
            str: ID de la playlist des uploads ou None si erreur
        """
        if not self.quota_manager.check_quota_available('channels', 1):
            logger.error("Quota insuffisant pour récupérer les informations de la chaîne")
            return None
        
        try:
            url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&forHandle={channel_handle}&key={self.api_key}"
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
            if not data.get("items"):
                logger.error(f"Chaîne non trouvée: {channel_handle}")
                return None
            
            uploads_playlist_id = data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            self.quota_manager.consume_quota('channels', 1)
            
            logger.info(f"Playlist uploads trouvée: {uploads_playlist_id}")
            return uploads_playlist_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération de la chaîne: {e}")
            return None
    
    def fetch_playlist_videos_paginated(self, playlist_id: str, max_results: int = 50) -> List[str]:
        """
        Récupère les IDs des vidéos d'une playlist avec pagination
        
        Args:
            playlist_id: ID de la playlist
            max_results: Nombre maximum de vidéos à récupérer
            
        Returns:
            List[str]: Liste des IDs des vidéos
        """
        video_ids = []
        next_page_token = None
        pages_fetched = 0
        max_pages = (max_results + self.max_videos_per_page - 1) // self.max_videos_per_page
        
        logger.info(f"Récupération de {max_results} vidéos (max {max_pages} pages)")
        
        while len(video_ids) < max_results and pages_fetched < max_pages:
            # Vérifier le quota avant chaque requête
            if not self.quota_manager.check_quota_available('playlistItems', 1):
                logger.warning("Quota insuffisant, arrêt de la pagination")
                break
            
            try:
                # Construire l'URL avec le token de pagination
                url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId={playlist_id}&maxResults={min(self.max_videos_per_page, max_results - len(video_ids))}&key={self.api_key}"
                
                if next_page_token:
                    url += f"&pageToken={next_page_token}"
                
                response = requests.get(url)
                response.raise_for_status()
                
                data = response.json()
                
                # Extraire les IDs des vidéos
                page_video_ids = [item["contentDetails"]["videoId"] for item in data.get("items", [])]
                video_ids.extend(page_video_ids)
                
                # Consommer le quota
                self.quota_manager.consume_quota('playlistItems', 1)
                pages_fetched += 1
                
                logger.info(f"Page {pages_fetched}: {len(page_video_ids)} vidéos récupérées (total: {len(video_ids)})")
                
                # Vérifier s'il y a une page suivante
                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    logger.info("Dernière page atteinte")
                    break
                
                # Petite pause pour éviter de surcharger l'API
                time.sleep(0.1)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Erreur lors de la récupération de la page {pages_fetched + 1}: {e}")
                break
        
        # Limiter au nombre demandé
        video_ids = video_ids[:max_results]
        logger.info(f"Total de {len(video_ids)} vidéos récupérées")
        
        return video_ids
    
    def fetch_videos_details_batch(self, video_ids: List[str]) -> List[Dict]:
        """
        Récupère les détails des vidéos par batch (max 50 par requête)
        
        Args:
            video_ids: Liste des IDs des vidéos
            
        Returns:
            List[Dict]: Liste des détails des vidéos
        """
        all_videos = []
        batch_size = 50  # Limite maximale de l'API YouTube
        
        # Diviser en batches
        for i in range(0, len(video_ids), batch_size):
            batch = video_ids[i:i + batch_size]
            
            # Vérifier le quota
            if not self.quota_manager.check_quota_available('videos', 1):
                logger.warning("Quota insuffisant pour récupérer les détails des vidéos")
                break
            
            try:
                video_ids_str = ",".join(batch)
                url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails,statistics&id={video_ids_str}&key={self.api_key}"
                
                response = requests.get(url)
                response.raise_for_status()
                
                data = response.json()
                videos = data.get("items", [])
                all_videos.extend(videos)
                
                # Consommer le quota
                self.quota_manager.consume_quota('videos', 1)
                
                logger.info(f"Batch {i//batch_size + 1}: {len(videos)} vidéos détaillées récupérées")
                
                # Petite pause entre les batches
                time.sleep(0.1)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Erreur lors de la récupération du batch {i//batch_size + 1}: {e}")
                continue
        
        return all_videos
    
    def fetch_channel_videos_complete(self, channel_handle: str, max_results: int = 50) -> Dict:
        """
        Récupère complètement les vidéos d'une chaîne avec pagination et gestion des quotas
        
        Args:
            channel_handle: Handle de la chaîne YouTube
            max_results: Nombre maximum de vidéos à récupérer
            
        Returns:
            Dict: Données complètes des vidéos
        """
        logger.info(f"Début de la récupération pour la chaîne: {channel_handle}")
        
        # Vérifier le quota global
        if not self.quota_manager.can_fetch_videos(max_results):
            quota_status = self.quota_manager.get_quota_status()
            return {
                "error": "Quota insuffisant",
                "quota_status": quota_status,
                "channel_handle": channel_handle,
                "requested_videos": max_results,
                "videos": []
            }
        
        # 1. Récupérer l'ID de la playlist des uploads
        playlist_id = self.fetch_channel_uploads_playlist_id(channel_handle)
        if not playlist_id:
            return {
                "error": "Impossible de récupérer la playlist des uploads",
                "channel_handle": channel_handle,
                "videos": []
            }
        
        # 2. Récupérer les IDs des vidéos avec pagination
        video_ids = self.fetch_playlist_videos_paginated(playlist_id, max_results)
        if not video_ids:
            return {
                "error": "Aucune vidéo trouvée",
                "channel_handle": channel_handle,
                "videos": []
            }
        
        # 3. Récupérer les détails des vidéos
        videos_data = self.fetch_videos_details_batch(video_ids)
        
        # 4. Construire la réponse finale
        result = {
            "channel_handle": channel_handle,
            "extraction_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_videos_requested": max_results,
            "total_videos_retrieved": len(videos_data),
            "quota_status": self.quota_manager.get_quota_status(),
            "videos": []
        }
        
        # 5. Formater les données des vidéos
        for item in videos_data:
            video = {
                "title": item["snippet"]["title"],
                "duration": item["contentDetails"]["duration"],
                "video_id": item["id"],
                "like_count": item["statistics"].get("likeCount", "0"),
                "view_count": item["statistics"].get("viewCount", "0"),
                "published_at": item["snippet"]["publishedAt"],
                "comment_count": item["statistics"].get("commentCount", "0"),
                "description": item["snippet"].get("description", "")[:500],  # Limiter la description
                "thumbnail_url": item["snippet"]["thumbnails"].get("medium", {}).get("url", ""),
                "tags": item["snippet"].get("tags", [])[:10]  # Limiter les tags
            }
            result["videos"].append(video)
        
        logger.info(f"Récupération terminée: {len(videos_data)} vidéos pour {channel_handle}")
        return result
