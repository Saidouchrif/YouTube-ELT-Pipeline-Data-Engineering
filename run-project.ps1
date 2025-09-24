# Script PowerShell pour lancer le projet YouTube ELT Pipeline
Write-Host "🚀 Démarrage du projet YouTube ELT Pipeline..." -ForegroundColor Green

# Fonction pour vérifier si un service est en cours d'exécution
function Test-ServiceRunning {
    param($ContainerName)
    $result = docker ps --filter "name=$ContainerName" --format "table {{.Names}}" | Select-String $ContainerName
    return $null -ne $result
}

# Étape 1: Créer le réseau Docker
Write-Host "📡 Création du réseau Docker 'airflow'..." -ForegroundColor Yellow
try {
    docker network create airflow 2>$null
    Write-Host "✅ Réseau créé avec succès" -ForegroundColor Green
} catch {
    Write-Host "ℹ️ Réseau déjà existant" -ForegroundColor Cyan
}

# Étape 2: Démarrer MongoDB et Mongo Express
Write-Host "🍃 Démarrage de MongoDB et Mongo Express..." -ForegroundColor Yellow
docker compose -f docker-compose.override.yml up -d
if (Test-ServiceRunning "youtube_mongodb") {
    Write-Host "✅ MongoDB démarré avec succès" -ForegroundColor Green
} else {
    Write-Host "❌ Erreur lors du démarrage de MongoDB" -ForegroundColor Red
    exit 1
}

# Étape 3: Démarrer Airflow
Write-Host "🌪️ Démarrage d'Airflow..." -ForegroundColor Yellow
docker compose up -d
Start-Sleep -Seconds 30

# Vérifier si Airflow est démarré
if (Test-ServiceRunning "youtube_airflow_webserver") {
    Write-Host "✅ Airflow webserver démarré avec succès" -ForegroundColor Green
} else {
    Write-Host "⏳ Airflow en cours de démarrage..." -ForegroundColor Yellow
}

if (Test-ServiceRunning "youtube_airflow_scheduler") {
    Write-Host "✅ Airflow scheduler démarré avec succès" -ForegroundColor Green
} else {
    Write-Host "⏳ Airflow scheduler en cours de démarrage..." -ForegroundColor Yellow
}

# Afficher les URLs d'accès
Write-Host "`n🎯 URLs d'accès:" -ForegroundColor Cyan
Write-Host "   • Airflow UI: http://localhost:8080 (admin/admin)" -ForegroundColor White
Write-Host "   • Mongo Express: http://localhost:8081" -ForegroundColor White

# Afficher les commandes utiles
Write-Host "`n🔧 Commandes utiles:" -ForegroundColor Cyan
Write-Host "   • Voir les logs Airflow: docker logs youtube_airflow_webserver" -ForegroundColor White
Write-Host "   • Voir les logs MongoDB: docker logs youtube_mongodb" -ForegroundColor White
Write-Host "   • Arrêter tout: docker compose down && docker compose -f docker-compose.override.yml down" -ForegroundColor White
Write-Host "   • Déclencher un DAG: docker exec youtube_airflow_webserver airflow dags trigger <dag_id>" -ForegroundColor White

# Attendre que tous les services soient prêts
Write-Host "`n⏳ Attente du démarrage complet des services..." -ForegroundColor Yellow
$maxWait = 120
$waited = 0
while ($waited -lt $maxWait) {
    $airflowReady = Test-ServiceRunning "youtube_airflow_webserver"
    $mongoReady = Test-ServiceRunning "youtube_mongodb"
    
    if ($airflowReady -and $mongoReady) {
        Write-Host "✅ Tous les services sont prêts!" -ForegroundColor Green
        break
    }
    
    Start-Sleep -Seconds 5
    $waited += 5
    Write-Host "." -NoNewline -ForegroundColor Yellow
}

if ($waited -ge $maxWait) {
    Write-Host "`n⚠️ Timeout atteint. Vérifiez les logs des conteneurs." -ForegroundColor Yellow
}

Write-Host "`n🎉 Projet démarré! Accédez à Airflow sur http://localhost:8080" -ForegroundColor Green
