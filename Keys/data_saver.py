import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DataSaver:
    """
    Gestionnaire de sauvegarde des données YouTube en fichiers JSON
    - Sauvegarde automatique avec horodatage
    - Organisation par chaîne et date
    - Métadonnées enrichies
    - Gestion des erreurs de sauvegarde
    """
    
    def __init__(self, base_data_dir: str = "../Data"):
        self.base_data_dir = Path(base_data_dir)
        self._ensure_data_structure()
    
    def _ensure_data_structure(self):
        """Crée la structure de dossiers nécessaire"""
        directories = [
            self.base_data_dir,
            self.base_data_dir / "channels",
            self.base_data_dir / "daily_extractions",
            self.base_data_dir / "metadata",
            self.base_data_dir / "logs"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Répertoire créé/vérifié: {directory}")
    
    def _generate_filename(self, channel_handle: str, extraction_date: str, file_type: str = "data") -> str:
        """
        Génère un nom de fichier unique avec horodatage
        
        Args:
            channel_handle: Handle de la chaîne YouTube
            extraction_date: Date d'extraction (ISO format)
            file_type: Type de fichier (data, metadata, etc.)
            
        Returns:
            str: Nom de fichier généré
        """
        # Convertir la date ISO en format plus lisible
        try:
            dt = datetime.fromisoformat(extraction_date.replace('Z', '+00:00'))
            date_str = dt.strftime("%Y%m%d_%H%M%S")
        except:
            # Fallback si la date n'est pas au bon format
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Nettoyer le nom de la chaîne pour le système de fichiers
        clean_channel = "".join(c for c in channel_handle if c.isalnum() or c in ('-', '_')).lower()
        
        return f"{clean_channel}_{date_str}_{file_type}.json"
    
    def _enrich_data_with_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrichit les données avec des métadonnées supplémentaires
        
        Args:
            data: Données originales de l'API
            
        Returns:
            Dict: Données enrichies avec métadonnées
        """
        enriched_data = data.copy()
        
        # Ajouter des métadonnées de sauvegarde
        enriched_data["_metadata"] = {
            "saved_at": datetime.now().isoformat(),
            "saved_by": "YouTube ELT Pipeline",
            "version": "2.0.0",
            "data_type": "channel_videos",
            "file_format": "json",
            "encoding": "utf-8"
        }
        
        # Ajouter des statistiques calculées
        if "videos" in data and data["videos"]:
            videos = data["videos"]
            enriched_data["_statistics"] = {
                "total_videos": len(videos),
                "total_views": sum(int(v.get("view_count", 0)) for v in videos),
                "total_likes": sum(int(v.get("like_count", 0)) for v in videos),
                "total_comments": sum(int(v.get("comment_count", 0)) for v in videos),
                "average_views": sum(int(v.get("view_count", 0)) for v in videos) // len(videos) if videos else 0,
                "most_viewed_video": max(videos, key=lambda x: int(x.get("view_count", 0)))["title"] if videos else None,
                "date_range": {
                    "oldest": min(v.get("published_at", "") for v in videos) if videos else None,
                    "newest": max(v.get("published_at", "") for v in videos) if videos else None
                }
            }
        
        return enriched_data
    
    def save_channel_data(self, data: Dict[str, Any], channel_handle: str) -> Dict[str, str]:
        """
        Sauvegarde les données d'une chaîne dans plusieurs formats
        
        Args:
            data: Données de la chaîne à sauvegarder
            channel_handle: Handle de la chaîne YouTube
            
        Returns:
            Dict: Chemins des fichiers sauvegardés
        """
        if not data or "extraction_date" not in data:
            raise ValueError("Données invalides: extraction_date manquante")
        
        extraction_date = data["extraction_date"]
        saved_files = {}
        
        try:
            # 1. Sauvegarde dans le dossier de la chaîne
            channel_dir = self.base_data_dir / "channels" / channel_handle.lower()
            channel_dir.mkdir(parents=True, exist_ok=True)
            
            filename = self._generate_filename(channel_handle, extraction_date, "data")
            channel_file = channel_dir / filename
            
            # Enrichir les données
            enriched_data = self._enrich_data_with_metadata(data)
            
            with open(channel_file, 'w', encoding='utf-8') as f:
                json.dump(enriched_data, f, indent=2, ensure_ascii=False)
            
            saved_files["channel_file"] = str(channel_file)
            logger.info(f"Données sauvegardées dans: {channel_file}")
            
            # 2. Sauvegarde dans le dossier des extractions quotidiennes
            daily_dir = self.base_data_dir / "daily_extractions"
            daily_filename = f"extraction_{datetime.now().strftime('%Y%m%d')}_{channel_handle.lower()}.json"
            daily_file = daily_dir / daily_filename
            
            with open(daily_file, 'w', encoding='utf-8') as f:
                json.dump(enriched_data, f, indent=2, ensure_ascii=False)
            
            saved_files["daily_file"] = str(daily_file)
            logger.info(f"Extraction quotidienne sauvegardée dans: {daily_file}")
            
            # 3. Sauvegarde des métadonnées séparées
            metadata_file = self.base_data_dir / "metadata" / f"{channel_handle.lower()}_metadata.json"
            metadata = {
                "channel_handle": channel_handle,
                "last_extraction": extraction_date,
                "total_extractions": self._count_extractions(channel_handle),
                "files_saved": saved_files,
                "data_summary": enriched_data.get("_statistics", {}),
                "quota_used": data.get("quota_status", {})
            }
            
            # Charger les métadonnées existantes si elles existent
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        existing_metadata = json.load(f)
                    metadata["extraction_history"] = existing_metadata.get("extraction_history", [])
                except:
                    metadata["extraction_history"] = []
            else:
                metadata["extraction_history"] = []
            
            # Ajouter cette extraction à l'historique
            metadata["extraction_history"].append({
                "date": extraction_date,
                "videos_count": len(data.get("videos", [])),
                "file_path": saved_files["channel_file"]
            })
            
            # Garder seulement les 50 dernières extractions
            metadata["extraction_history"] = metadata["extraction_history"][-50:]
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            saved_files["metadata_file"] = str(metadata_file)
            logger.info(f"Métadonnées sauvegardées dans: {metadata_file}")
            
            # 4. Créer un fichier de log de l'extraction
            self._log_extraction(channel_handle, data, saved_files)
            
            return saved_files
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des données pour {channel_handle}: {e}")
            raise
    
    def _count_extractions(self, channel_handle: str) -> int:
        """Compte le nombre d'extractions pour une chaîne"""
        channel_dir = self.base_data_dir / "channels" / channel_handle.lower()
        if not channel_dir.exists():
            return 0
        
        json_files = list(channel_dir.glob("*.json"))
        return len(json_files)
    
    def _log_extraction(self, channel_handle: str, data: Dict[str, Any], saved_files: Dict[str, str]):
        """Crée un log de l'extraction"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "channel_handle": channel_handle,
            "extraction_date": data.get("extraction_date"),
            "videos_count": len(data.get("videos", [])),
            "quota_used": data.get("quota_status", {}).get("daily_usage", 0),
            "files_saved": saved_files,
            "status": "success"
        }
        
        log_file = self.base_data_dir / "logs" / f"extractions_{datetime.now().strftime('%Y%m%d')}.json"
        
        # Charger les logs existants
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        
        # Sauvegarder les logs
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    
    def get_channel_extractions(self, channel_handle: str) -> list:
        """
        Récupère la liste des extractions pour une chaîne
        
        Args:
            channel_handle: Handle de la chaîne YouTube
            
        Returns:
            list: Liste des fichiers d'extraction
        """
        channel_dir = self.base_data_dir / "channels" / channel_handle.lower()
        if not channel_dir.exists():
            return []
        
        json_files = list(channel_dir.glob("*.json"))
        return [str(f) for f in sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)]
    
    def get_daily_extractions(self, date: Optional[str] = None) -> list:
        """
        Récupère les extractions d'une date donnée
        
        Args:
            date: Date au format YYYYMMDD (par défaut: aujourd'hui)
            
        Returns:
            list: Liste des fichiers d'extraction du jour
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        daily_dir = self.base_data_dir / "daily_extractions"
        pattern = f"extraction_{date}_*.json"
        
        json_files = list(daily_dir.glob(pattern))
        return [str(f) for f in sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)]
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques globales des extractions
        
        Returns:
            Dict: Statistiques des extractions
        """
        stats = {
            "total_channels": 0,
            "total_extractions": 0,
            "total_files": 0,
            "channels": {},
            "daily_stats": {}
        }
        
        # Compter les chaînes et extractions
        channels_dir = self.base_data_dir / "channels"
        if channels_dir.exists():
            for channel_dir in channels_dir.iterdir():
                if channel_dir.is_dir():
                    channel_name = channel_dir.name
                    json_files = list(channel_dir.glob("*.json"))
                    
                    stats["total_channels"] += 1
                    stats["total_extractions"] += len(json_files)
                    stats["total_files"] += len(json_files)
                    
                    stats["channels"][channel_name] = {
                        "extractions_count": len(json_files),
                        "last_extraction": max([f.stat().st_mtime for f in json_files]) if json_files else None
                    }
        
        # Statistiques quotidiennes
        daily_dir = self.base_data_dir / "daily_extractions"
        if daily_dir.exists():
            for daily_file in daily_dir.glob("extraction_*.json"):
                date_str = daily_file.name.split('_')[1]  # extraction_YYYYMMDD_channel.json
                if date_str not in stats["daily_stats"]:
                    stats["daily_stats"][date_str] = 0
                stats["daily_stats"][date_str] += 1
        
        return stats
    
    def cleanup_old_files(self, days_to_keep: int = 30):
        """
        Nettoie les anciens fichiers de données
        
        Args:
            days_to_keep: Nombre de jours à conserver
        """
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        
        # Nettoyer les logs
        logs_dir = self.base_data_dir / "logs"
        if logs_dir.exists():
            for log_file in logs_dir.glob("*.json"):
                if log_file.stat().st_mtime < cutoff_date:
                    log_file.unlink()
                    logger.info(f"Fichier de log supprimé: {log_file}")
        
        logger.info(f"Nettoyage terminé: fichiers de plus de {days_to_keep} jours supprimés")
