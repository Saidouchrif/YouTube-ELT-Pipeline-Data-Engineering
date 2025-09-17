# Gestion des Quotas et Pagination - YouTube ELT Pipeline

## 🎯 Vue d'ensemble

Ce module implémente une gestion avancée des quotas API YouTube (10 000 unités/jour) et une pagination automatique pour récupérer efficacement de grandes quantités de vidéos.

## 🚀 Fonctionnalités

### ✅ Gestion des Quotas API
- **Suivi en temps réel** des quotas utilisés (10 000 unités/jour)
- **Calcul automatique** des coûts par endpoint
- **Vérification préventive** avant chaque requête
- **Persistance** des données de quota dans un fichier JSON
- **Remise à zéro automatique** quotidienne

### ✅ Pagination Intelligente
- **Récupération automatique** de toutes les pages de résultats
- **Optimisation des requêtes** (50 vidéos par page maximum)
- **Gestion des tokens** de pagination
- **Limitation intelligente** basée sur les quotas disponibles

### ✅ Gestion d'Erreurs Avancée
- **Messages d'erreur détaillés** avec suggestions
- **Codes de statut HTTP** appropriés (429 pour quota dépassé)
- **Fallback** vers la méthode legacy si nécessaire
- **Logging complet** des opérations

## 📁 Structure des Fichiers

```
Keys/
├── quota_manager.py          # Gestionnaire de quotas
├── pagination_manager.py     # Gestionnaire de pagination
├── config.py                 # Configuration centralisée
├── test_quota_pagination.py  # Script de test
├── Api/
│   └── main.py              # API FastAPI mise à jour
└── quota_usage.json         # Fichier de suivi des quotas (généré automatiquement)
```

## 🔧 Utilisation

### 1. API FastAPI

#### Endpoint Principal
```bash
POST /channel
Content-Type: application/json

{
  "channel_handle": "MrBeast",
  "max_results": 100,
  "use_pagination": true
}
```

#### Vérifier le Statut des Quotas
```bash
GET /quota/status
```

#### Estimer le Coût d'une Requête
```bash
GET /quota/estimate?channel_handle=MrBeast&max_results=50
```

### 2. Utilisation Directe

```python
from quota_manager import QuotaManager
from pagination_manager import PaginationManager

# Initialiser les gestionnaires
quota_manager = QuotaManager()
pagination_manager = PaginationManager(API_KEY, quota_manager)

# Récupérer des vidéos avec gestion des quotas
result = pagination_manager.fetch_channel_videos_complete("MrBeast", 50)
```

## 📊 Coûts des Endpoints

| Endpoint | Coût (unités) | Description |
|----------|---------------|-------------|
| `channels` | 1 | Informations de la chaîne |
| `playlistItems` | 1 | Liste des vidéos d'une playlist |
| `videos` | 1 | Détails des vidéos |
| `search` | 100 | Recherche (non utilisé ici) |

### Exemple de Calcul
Pour récupérer **100 vidéos** :
- 1 appel `channels` = 1 unité
- 2 appels `playlistItems` (50 vidéos/page) = 2 unités  
- 2 appels `videos` (50 vidéos/batch) = 2 unités
- **Total = 5 unités**

## 🧪 Tests

Exécuter le script de test :
```bash
cd Keys
python test_quota_pagination.py
```

Le script teste :
- ✅ Gestionnaire de quotas
- ✅ Gestionnaire de pagination
- ✅ Limites de quota
- ✅ Sauvegarde des résultats

## 📈 Monitoring

### Fichier de Quotas (`quota_usage.json`)
```json
{
  "daily_usage": {
    "2024-01-15": 150,
    "2024-01-16": 75
  },
  "total_usage": 225,
  "last_reset": "2024-01-16T00:00:00"
}
```

### Statut des Quotas
```json
{
  "date": "2024-01-16",
  "daily_usage": 75,
  "daily_limit": 10000,
  "remaining": 9925,
  "percentage_used": 0.75,
  "status": "OK"
}
```

## ⚠️ Gestion des Erreurs

### Quota Insuffisant (HTTP 429)
```json
{
  "error": "Quota insuffisant",
  "message": "Impossible de récupérer 1000 vidéos avec le quota restant",
  "quota_status": {...},
  "suggestion": "Essayez avec 50 vidéos maximum"
}
```

### Chaîne Non Trouvée (HTTP 400)
```json
{
  "error": "Chaîne non trouvée",
  "channel_handle": "ChaîneInexistante",
  "videos": []
}
```

## 🔄 Migration depuis l'Ancienne Version

### Compatibilité
- ✅ L'endpoint `/channel/legacy` maintient la compatibilité
- ✅ Paramètre `use_pagination: false` utilise l'ancienne méthode
- ✅ Toutes les réponses incluent les mêmes champs

### Nouveaux Champs
```json
{
  "channel_handle": "MrBeast",
  "total_videos_requested": 100,
  "total_videos_retrieved": 95,
  "quota_status": {...},
  "videos": [...]
}
```

## 🚀 Démarrage Rapide

1. **Installer les dépendances** :
```bash
pip install fastapi uvicorn requests
```

2. **Démarrer l'API** :
```bash
cd Keys/Api
uvicorn main:app --reload
```

3. **Tester** :
```bash
curl -X POST "http://localhost:8000/channel" \
  -H "Content-Type: application/json" \
  -d '{"channel_handle": "MrBeast", "max_results": 10}'
```

## 📝 Logs

Les logs sont générés automatiquement avec :
- 📊 Suivi des quotas
- 🔄 Progression de la pagination
- ⚠️ Gestion des erreurs
- ✅ Succès des opérations

## 🎯 Avantages

1. **Économie de Quotas** : Optimisation automatique des requêtes
2. **Scalabilité** : Récupération de milliers de vidéos
3. **Fiabilité** : Gestion robuste des erreurs
4. **Monitoring** : Suivi en temps réel des quotas
5. **Flexibilité** : Compatibilité avec l'ancienne version

---

*Développé pour le pipeline YouTube ELT - Data Engineering*
