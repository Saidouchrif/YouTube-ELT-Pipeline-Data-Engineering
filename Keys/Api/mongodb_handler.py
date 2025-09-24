"""
Gestionnaire MongoDB pour l'API FastAPI
"""
import os
import datetime
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
import logging

logger = logging.getLogger(__name__)

class MongoDBHandler:
    def __init__(self):
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """Établit la connexion à MongoDB"""
        try:
            mongo_host = os.getenv('MONGO_HOST', 'mongodb')
            mongo_port = int(os.getenv('MONGO_PORT', '27017'))
            mongo_username = os.getenv('MONGO_USERNAME', 'admin')
            mongo_password = os.getenv('MONGO_PASSWORD', 'password123')
            mongo_database = os.getenv('MONGO_DATABASE', 'youtube_data')
            
            # Construire l'URI de connexion
            connection_string = f"mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}/{mongo_database}?authSource=admin"
            
            self.client = MongoClient(connection_string)
            self.db = self.client[mongo_database]
            
            # Test de la connexion
            self.client.admin.command('ping')
            logger.info(f"Connexion MongoDB établie: {mongo_host}:{mongo_port}")
            
        except Exception as e:
            logger.error(f"Erreur de connexion MongoDB: {e}")
            self.client = None
            self.db = None
    
    def is_connected(self) -> bool:
        """Vérifie si la connexion MongoDB est active"""
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
        except:
            pass
        return False
    
    def save_to_staging(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Sauvegarde les données dans la collection staging_data"""
        if not self.is_connected():
            logger.warning("MongoDB non connecté, impossible de sauvegarder en staging")
            return None
        
        try:
            collection = self.db.staging_data
            
            # Ajouter des métadonnées
            document = {
                "extraction_date": datetime.datetime.utcnow(),
                "channel_handle": data.get("channel_handle"),
                "total_videos": data.get("total_videos", 0),
                "data_source": "fastapi",
                "raw_data": data
            }
            
            # Insérer le document
            result = collection.insert_one(document)
            
            logger.info(f"Données sauvegardées en staging: {result.inserted_id}")
            
            return {
                "inserted_id": str(result.inserted_id),
                "collection": "staging_data",
                "timestamp": document["extraction_date"].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde staging: {e}")
            return None
    
    def save_videos_to_core(self, videos: List[Dict[str, Any]], channel_handle: str) -> Optional[Dict[str, Any]]:
        """Sauvegarde les vidéos individuelles dans la collection core_data"""
        if not self.is_connected():
            logger.warning("MongoDB non connecté, impossible de sauvegarder en core")
            return None
        
        try:
            collection = self.db.core_data
            
            documents = []
            for video in videos:
                document = {
                    "video_id": video.get("video_id"),
                    "channel_handle": channel_handle,
                    "title": video.get("title"),
                    "published_at": video.get("published_at"),
                    "duration": video.get("duration"),
                    "view_count": int(video.get("view_count", 0)),
                    "like_count": int(video.get("like_count", 0)),
                    "comment_count": int(video.get("comment_count", 0)),
                    "description": video.get("description", ""),
                    "thumbnail_url": video.get("thumbnail_url", ""),
                    "tags": video.get("tags", []),
                    "created_at": datetime.datetime.utcnow(),
                    "updated_at": datetime.datetime.utcnow()
                }
                documents.append(document)
            
            # Utiliser upsert pour éviter les doublons
            upserted_count = 0
            for doc in documents:
                result = collection.replace_one(
                    {"video_id": doc["video_id"]},
                    doc,
                    upsert=True
                )
                if result.upserted_id or result.modified_count > 0:
                    upserted_count += 1
            
            logger.info(f"Vidéos sauvegardées en core: {upserted_count}/{len(documents)}")
            
            return {
                "upserted_count": upserted_count,
                "total_videos": len(documents),
                "collection": "core_data"
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde core: {e}")
            return None
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques des collections"""
        if not self.is_connected():
            return {"error": "MongoDB non connecté"}
        
        try:
            stats = {}
            collections = ["staging_data", "core_data", "history_data"]
            
            for collection_name in collections:
                collection = self.db[collection_name]
                count = collection.count_documents({})
                stats[collection_name] = count
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats: {e}")
            return {"error": str(e)}
    
    def get_recent_videos(self, channel_handle: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère les vidéos récentes d'une chaîne depuis core_data"""
        if not self.is_connected():
            return []
        
        try:
            collection = self.db.core_data
            
            videos = list(collection.find(
                {"channel_handle": channel_handle}
            ).sort("created_at", -1).limit(limit))
            
            # Convertir ObjectId en string
            for video in videos:
                video["_id"] = str(video["_id"])
            
            return videos
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des vidéos: {e}")
            return []
    
    def close(self):
        """Ferme la connexion MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Connexion MongoDB fermée")
