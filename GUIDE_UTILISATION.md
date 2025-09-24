# 🚀 Guide d'Utilisation - YouTube ELT Pipeline

## ✅ Services Déployés et Fonctionnels

### 📊 Statut des Services
- **✅ MongoDB** : Port 27017 - Base de données principale
- **✅ Mongo Express** : http://localhost:8081 - Interface web MongoDB
- **✅ FastAPI** : http://localhost:8000 - API de récupération YouTube
- **⏳ Airflow** : http://localhost:8080 - Orchestrateur de pipeline (en cours)

## 🔐 Identifiants d'Accès

### MongoDB
- **Host** : localhost:27017
- **Username** : admin
- **Password** : password123
- **Database** : youtube_data

### Mongo Express
- **URL** : http://localhost:8081
- **Username** : admin
- **Password** : admin123

### Airflow
- **URL** : http://localhost:8080
- **Username** : admin
- **Password** : admin

## 🛠️ Commandes Docker

### Démarrer tous les services
```bash
docker compose -f docker-compose.final.yml up -d
```

### Arrêter tous les services
```bash
docker compose -f docker-compose.final.yml down
```

### Voir les logs d'un service
```bash
docker logs youtube_fastapi
docker logs youtube_mongodb
docker logs youtube_mongo_express
docker logs youtube_airflow
```

### Redémarrer un service spécifique
```bash
docker compose -f docker-compose.final.yml restart youtube-api
```

## 🔧 Utilisation de l'API FastAPI

### Endpoints Disponibles

#### 1. Health Check
```bash
GET http://localhost:8000/health
```

#### 2. Informations sur l'API
```bash
GET http://localhost:8000/
```

#### 3. Statut des Quotas
```bash
GET http://localhost:8000/quota/status
```

#### 4. Récupérer des Données YouTube
```bash
POST http://localhost:8000/channel
Content-Type: application/json

{
  "channel_handle": "MrBeast",
  "max_results": 5,
  "use_pagination": false,
  "save_to_file": false
}
```

### Exemple avec PowerShell
```powershell
# Test de l'API
.\test-api.ps1

# Ou manuellement
$body = @{
    channel_handle = "MrBeast"
    max_results = 3
    use_pagination = $false
    save_to_file = $false
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/channel" -Method Post -Body $body -ContentType "application/json"
```

## 📁 Structure des Données

### Collections MongoDB
- **staging_data** : Données brutes extraites
- **core_data** : Données transformées et nettoyées
- **history_data** : Historique des modifications (SCD2)

### Répertoires de Données
- `./data/staging/` : Fichiers JSON temporaires
- `./Keys/Data/` : Données sauvegardées par l'API

## 🔍 Monitoring et Debug

### Vérifier l'état des conteneurs
```bash
docker ps
```

### Tester la connectivité
```bash
# Test MongoDB
docker exec youtube_mongodb mongosh --eval "db.adminCommand('ping')"

# Test API
curl http://localhost:8000/health

# Test Mongo Express
curl http://localhost:8081
```

### Logs en temps réel
```bash
docker logs -f youtube_fastapi
```

## 🚨 Résolution de Problèmes

### API FastAPI ne répond pas
1. Vérifier les logs : `docker logs youtube_fastapi`
2. Redémarrer : `docker compose -f docker-compose.final.yml restart youtube-api`
3. Vérifier les ports : `netstat -an | findstr :8000`

### Mongo Express inaccessible
1. Utiliser les identifiants : admin/admin123
2. Vérifier la connexion MongoDB
3. Redémarrer : `docker compose -f docker-compose.final.yml restart mongo-express`

### Airflow lent à démarrer
1. Attendre 2-3 minutes pour l'initialisation complète
2. Vérifier les logs : `docker logs youtube_airflow`
3. L'interface sera disponible sur http://localhost:8080

## 📈 Prochaines Étapes

1. **Finaliser Airflow** : Vérifier que tous les DAGs se chargent correctement
2. **Tests d'intégration** : Exécuter le pipeline complet
3. **Optimisation** : Ajuster les quotas et la pagination
4. **Monitoring** : Ajouter des alertes et métriques

## 🎯 URLs de Référence

- **API Documentation** : http://localhost:8000/docs (Swagger UI)
- **MongoDB Interface** : http://localhost:8081
- **Airflow Dashboard** : http://localhost:8080
- **API Health** : http://localhost:8000/health
