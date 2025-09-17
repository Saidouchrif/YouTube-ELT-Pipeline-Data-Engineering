import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuotaManager:
    """
    Gestionnaire de quotas pour l'API YouTube Data v3
    - Quota quotidien: 10 000 unités
    - Suivi des quotas utilisés par jour
    - Calcul automatique des coûts d'API
    """
    
    # Coûts en unités de quota pour chaque endpoint
    QUOTA_COSTS = {
        'channels': 1,           # channels.list
        'playlistItems': 1,      # playlistItems.list
        'videos': 1,             # videos.list
        'search': 100,           # search.list
        'commentThreads': 1,     # commentThreads.list
        'comments': 1            # comments.list
    }
    
    def __init__(self, quota_file: str = "quota_usage.json"):
        self.quota_file = quota_file
        self.daily_limit = 10000
        self.quota_data = self._load_quota_data()
    
    def _load_quota_data(self) -> Dict:
        """Charge les données de quota depuis le fichier JSON"""
        if os.path.exists(self.quota_file):
            try:
                with open(self.quota_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logger.warning(f"Erreur lors du chargement de {self.quota_file}, initialisation avec des données vides")
        
        return {
            "daily_usage": {},
            "total_usage": 0,
            "last_reset": datetime.now().isoformat()
        }
    
    def _save_quota_data(self):
        """Sauvegarde les données de quota dans le fichier JSON"""
        try:
            with open(self.quota_file, 'w') as f:
                json.dump(self.quota_data, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des quotas: {e}")
    
    def _get_today_key(self) -> str:
        """Retourne la clé pour la date d'aujourd'hui"""
        return datetime.now().strftime("%Y-%m-%d")
    
    def _reset_daily_usage_if_needed(self):
        """Remet à zéro l'usage quotidien si c'est un nouveau jour"""
        today = self._get_today_key()
        last_reset = datetime.fromisoformat(self.quota_data["last_reset"])
        
        if datetime.now().date() > last_reset.date():
            # Nouveau jour, remettre à zéro
            self.quota_data["daily_usage"] = {}
            self.quota_data["last_reset"] = datetime.now().isoformat()
            logger.info("Nouveau jour détecté, remise à zéro des quotas quotidiens")
    
    def check_quota_available(self, endpoint: str, estimated_requests: int = 1) -> bool:
        """
        Vérifie si le quota est disponible pour une requête
        
        Args:
            endpoint: Type d'endpoint API (channels, videos, etc.)
            estimated_requests: Nombre estimé de requêtes
            
        Returns:
            bool: True si le quota est disponible, False sinon
        """
        self._reset_daily_usage_if_needed()
        
        cost_per_request = self.QUOTA_COSTS.get(endpoint, 1)
        total_cost = cost_per_request * estimated_requests
        
        today = self._get_today_key()
        current_usage = self.quota_data["daily_usage"].get(today, 0)
        
        if current_usage + total_cost > self.daily_limit:
            logger.warning(f"Quota insuffisant: {current_usage + total_cost}/{self.daily_limit}")
            return False
        
        return True
    
    def consume_quota(self, endpoint: str, requests_count: int = 1):
        """
        Consomme du quota pour des requêtes effectuées
        
        Args:
            endpoint: Type d'endpoint API
            requests_count: Nombre de requêtes effectuées
        """
        self._reset_daily_usage_if_needed()
        
        cost_per_request = self.QUOTA_COSTS.get(endpoint, 1)
        total_cost = cost_per_request * requests_count
        
        today = self._get_today_key()
        
        if today not in self.quota_data["daily_usage"]:
            self.quota_data["daily_usage"][today] = 0
        
        self.quota_data["daily_usage"][today] += total_cost
        self.quota_data["total_usage"] += total_cost
        
        logger.info(f"Quota consommé: {total_cost} unités pour {endpoint} ({requests_count} requêtes)")
        logger.info(f"Usage quotidien: {self.quota_data['daily_usage'][today]}/{self.daily_limit}")
        
        self._save_quota_data()
    
    def get_quota_status(self) -> Dict:
        """
        Retourne le statut actuel des quotas
        
        Returns:
            Dict contenant les informations de quota
        """
        self._reset_daily_usage_if_needed()
        
        today = self._get_today_key()
        current_usage = self.quota_data["daily_usage"].get(today, 0)
        remaining = self.daily_limit - current_usage
        percentage_used = (current_usage / self.daily_limit) * 100
        
        return {
            "date": today,
            "daily_usage": current_usage,
            "daily_limit": self.daily_limit,
            "remaining": remaining,
            "percentage_used": round(percentage_used, 2),
            "total_usage": self.quota_data["total_usage"],
            "status": "OK" if remaining > 0 else "LIMIT_REACHED"
        }
    
    def get_estimated_cost(self, endpoint: str, requests_count: int) -> int:
        """
        Calcule le coût estimé en unités de quota
        
        Args:
            endpoint: Type d'endpoint API
            requests_count: Nombre de requêtes
            
        Returns:
            int: Coût total en unités de quota
        """
        cost_per_request = self.QUOTA_COSTS.get(endpoint, 1)
        return cost_per_request * requests_count
    
    def can_fetch_videos(self, max_results: int) -> bool:
        """
        Vérifie si on peut récupérer un nombre donné de vidéos
        (considère les 3 appels API nécessaires: channels + playlistItems + videos)
        
        Args:
            max_results: Nombre maximum de vidéos à récupérer
            
        Returns:
            bool: True si possible, False sinon
        """
        # 1 appel channels + 1 appel playlistItems + 1 appel videos
        total_requests = 3
        return self.check_quota_available('videos', total_requests)
    
    def get_max_videos_possible(self) -> int:
        """
        Calcule le nombre maximum de vidéos qu'on peut récupérer avec le quota restant
        
        Returns:
            int: Nombre maximum de vidéos possible
        """
        status = self.get_quota_status()
        remaining = status["remaining"]
        
        # Coût pour récupérer des vidéos: 3 unités (channels + playlistItems + videos)
        # Plus 1 unité par page de 50 vidéos maximum
        if remaining < 3:
            return 0
        
        # On peut faire au moins 1 requête complète
        # Chaque page de playlistItems peut contenir max 50 vidéos
        return min(50, remaining - 3)  # -3 pour les appels obligatoires
