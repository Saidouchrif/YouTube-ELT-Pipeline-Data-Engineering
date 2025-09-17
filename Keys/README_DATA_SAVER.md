# Système de Sauvegarde Automatique - YouTube ELT Pipeline

## 🎯 Vue d'ensemble

Le système de sauvegarde automatique permet de stocker toutes les données récupérées de l'API YouTube dans des fichiers JSON organisés avec horodatage et métadonnées enrichies.

## 🚀 Fonctionnalités

### ✅ Sauvegarde Automatique
- **Sauvegarde automatique** lors de chaque requête API
- **Horodatage précis** dans les noms de fichiers
- **Organisation par chaîne** et par date
- **Métadonnées enrichies** avec statistiques calculées

### ✅ Structure Organisée
```
Data/
├── channels/                    # Données par chaîne
│   └── elgrandetoto/
│       ├── elgrandetoto_20250918_102030_data.json
│       └── elgrandetoto_20250918_143045_data.json
├── daily_extractions/           # Extractions quotidiennes
│   ├── extraction_20250918_elgrandetoto.json
│   └── extraction_20250918_mrbeast.json
├── metadata/                    # Métadonnées des chaînes
│   ├── elgrandetoto_metadata.json
│   └── mrbeast_metadata.json
└── logs/                        # Logs des extractions
    └── extractions_20250918.json
```

### ✅ Métadonnées Enrichies
- **Statistiques calculées** (total vues, likes, commentaires)
- **Vidéo la plus vue** automatiquement identifiée
- **Plage de dates** des vidéos
- **Historique des extractions** par chaîne

## 📁 Structure des Fichiers

### Fichier de Données Principal
```json
{
  "channel_handle": "ElGrandeToto",
  "extraction_date": "2025-09-18T10:20:30Z",
  "total_videos_requested": 10,
  "total_videos_retrieved": 10,
  "quota_status": {...},
  "videos": [...],
  "_metadata": {
    "saved_at": "2025-09-18T10:20:35Z",
    "saved_by": "YouTube ELT Pipeline",
    "version": "2.0.0",
    "data_type": "channel_videos"
  },
  "_statistics": {
    "total_videos": 10,
    "total_views": 15000000,
    "total_likes": 500000,
    "average_views": 1500000,
    "most_viewed_video": "Titre de la vidéo la plus vue",
    "date_range": {
      "oldest": "2025-08-01T10:00:00Z",
      "newest": "2025-09-18T10:00:00Z"
    }
  }
}
```

### Fichier de Métadonnées
```json
{
  "channel_handle": "ElGrandeToto",
  "last_extraction": "2025-09-18T10:20:30Z",
  "total_extractions": 15,
  "extraction_history": [
    {
      "date": "2025-09-18T10:20:30Z",
      "videos_count": 10,
      "file_path": "/path/to/file.json"
    }
  ],
  "data_summary": {...},
  "quota_used": {...}
}
```

## 🔧 Utilisation

### 1. Sauvegarde Automatique via API

```bash
# Requête avec sauvegarde automatique
curl -X POST "http://localhost:8000/channel" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_handle": "ElGrandeToto",
    "max_results": 10,
    "save_to_file": true
  }'
```

**Réponse avec informations de sauvegarde :**
```json
{
  "channel_handle": "ElGrandeToto",
  "total_videos_retrieved": 10,
  "videos": [...],
  "_saved_files": {
    "channel_file": "/Data/channels/elgrandetoto/elgrandetoto_20250918_102030_data.json",
    "daily_file": "/Data/daily_extractions/extraction_20250918_elgrandetoto.json",
    "metadata_file": "/Data/metadata/elgrandetoto_metadata.json"
  },
  "_saved_at": "2025-09-18T10:20:35Z"
}
```

### 2. Gestion des Données Sauvegardées

#### Lister les Extractions
```bash
# Toutes les extractions
GET /data/extractions

# Extractions d'une chaîne spécifique
GET /data/extractions?channel_handle=ElGrandeToto

# Extractions d'une date spécifique
GET /data/extractions?date=20250918
```

#### Statistiques Globales
```bash
GET /data/stats
```

#### Historique d'une Chaîne
```bash
GET /data/channel/ElGrandeToto
```

### 3. Utilisation Directe

```python
from data_saver import DataSaver

# Initialiser le gestionnaire
data_saver = DataSaver()

# Sauvegarder des données
saved_files = data_saver.save_channel_data(data, "ElGrandeToto")

# Récupérer l'historique
extractions = data_saver.get_channel_extractions("ElGrandeToto")

# Statistiques globales
stats = data_saver.get_extraction_stats()
```

## 📊 Endpoints API

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/channel` | POST | Récupérer et sauvegarder les données d'une chaîne |
| `/data/extractions` | GET | Lister les extractions sauvegardées |
| `/data/stats` | GET | Statistiques globales des données |
| `/data/channel/{handle}` | GET | Historique complet d'une chaîne |

## 🎯 Avantages

### 1. **Traçabilité Complète**
- Historique de toutes les extractions
- Horodatage précis de chaque opération
- Métadonnées enrichies automatiquement

### 2. **Organisation Optimale**
- Structure de dossiers logique
- Noms de fichiers informatifs
- Séparation des données et métadonnées

### 3. **Analyse Facilitée**
- Statistiques calculées automatiquement
- Comparaison facile entre extractions
- Données prêtes pour l'analyse

### 4. **Gestion Automatique**
- Sauvegarde transparente
- Pas d'intervention manuelle requise
- Gestion des erreurs intégrée

## 🔍 Exemples d'Utilisation

### Analyse de l'Évolution d'une Chaîne
```python
# Récupérer l'historique complet
history = data_saver.get_channel_data_history("ElGrandeToto")

# Analyser l'évolution des vues
for extraction in history["extractions"]:
    with open(extraction, 'r') as f:
        data = json.load(f)
        total_views = data["_statistics"]["total_views"]
        print(f"Extraction du {data['extraction_date']}: {total_views} vues")
```

### Comparaison Quotidienne
```python
# Récupérer les extractions d'aujourd'hui
today = datetime.now().strftime('%Y%m%d')
extractions = data_saver.get_daily_extractions(today)

print(f"Extractions du {today}: {len(extractions)} chaînes")
```

### Statistiques Globales
```python
# Statistiques complètes
stats = data_saver.get_extraction_stats()
print(f"Total des chaînes suivies: {stats['total_channels']}")
print(f"Total des extractions: {stats['total_extractions']}")
```

## 🧪 Tests

Exécuter les tests de sauvegarde :
```bash
cd Keys
python test_data_saver.py
```

Le script teste :
- ✅ Sauvegarde automatique
- ✅ Structure des fichiers
- ✅ Enrichissement des métadonnées
- ✅ Intégration API

## 📝 Logs et Monitoring

### Fichiers de Log
- **Logs quotidiens** : `Data/logs/extractions_YYYYMMDD.json`
- **Métadonnées** : `Data/metadata/{channel}_metadata.json`
- **Statistiques** : Accessibles via l'API

### Informations Loggées
- Timestamp de chaque extraction
- Nombre de vidéos récupérées
- Quota utilisé
- Fichiers créés
- Statut de l'opération

## ⚙️ Configuration

### Paramètres de Sauvegarde
```python
# Dans data_saver.py
base_data_dir = "../Data"  # Répertoire de base
max_history = 50           # Nombre max d'extractions dans l'historique
cleanup_days = 30          # Jours avant suppression des anciens logs
```

### Personnalisation
- **Répertoire de base** : Modifiable dans `DataSaver.__init__()`
- **Format des noms** : Personnalisable dans `_generate_filename()`
- **Métadonnées** : Extensibles dans `_enrich_data_with_metadata()`

## 🚀 Démarrage Rapide

1. **L'API sauvegarde automatiquement** lors de chaque requête
2. **Vérifier les données** : `GET /data/stats`
3. **Consulter l'historique** : `GET /data/extractions`
4. **Analyser les métadonnées** : `GET /data/channel/{handle}`

---

*Système de sauvegarde intégré au pipeline YouTube ELT - Data Engineering*
