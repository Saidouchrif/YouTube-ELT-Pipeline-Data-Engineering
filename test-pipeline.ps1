# Script de test du pipeline YouTube ELT
Write-Host "🧪 Test du pipeline YouTube ELT..." -ForegroundColor Green

# Fonction pour attendre qu'un service soit prêt
function Wait-ForService {
    param($Url, $ServiceName, $MaxWait = 120)
    
    Write-Host "⏳ Attente de $ServiceName..." -ForegroundColor Yellow
    $waited = 0
    
    while ($waited -lt $MaxWait) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Host "✅ $ServiceName est prêt!" -ForegroundColor Green
                return $true
            }
        } catch {
            # Service pas encore prêt
        }
        
        Start-Sleep -Seconds 5
        $waited += 5
        Write-Host "." -NoNewline -ForegroundColor Yellow
    }
    
    Write-Host "`n❌ Timeout pour $ServiceName" -ForegroundColor Red
    return $false
}

# Vérifier que les services sont en cours d'exécution
Write-Host "`n📋 Vérification des services..." -ForegroundColor Cyan
$services = @("youtube_mongodb", "youtube_mongo_express", "youtube_airflow_webserver", "youtube_airflow_scheduler")

foreach ($service in $services) {
    $running = docker ps --filter "name=$service" --format "{{.Names}}" | Select-String $service
    if ($running) {
        Write-Host "✅ $service est en cours d'exécution" -ForegroundColor Green
    } else {
        Write-Host "❌ $service n'est pas en cours d'exécution" -ForegroundColor Red
    }
}

# Attendre qu'Airflow soit prêt
if (Wait-ForService "http://localhost:8080" "Airflow") {
    
    # Lister les DAGs disponibles
    Write-Host "`n📊 DAGs disponibles:" -ForegroundColor Cyan
    docker exec youtube_airflow_webserver airflow dags list
    
    # Déclencher le DAG d'extraction
    Write-Host "`n🚀 Déclenchement du DAG produce_JSON..." -ForegroundColor Yellow
    docker exec youtube_airflow_webserver airflow dags trigger produce_JSON
    
    # Attendre un peu et vérifier le statut
    Start-Sleep -Seconds 10
    Write-Host "`n📈 Statut des tâches:" -ForegroundColor Cyan
    docker exec youtube_airflow_webserver airflow tasks states-for-dag-run produce_JSON
    
    # Déclencher le DAG de chargement
    Write-Host "`n🔄 Déclenchement du DAG update_db..." -ForegroundColor Yellow
    docker exec youtube_airflow_webserver airflow dags trigger update_db
    
    # Déclencher le DAG de qualité des données
    Write-Host "`n🔍 Déclenchement du DAG data_quality..." -ForegroundColor Yellow
    docker exec youtube_airflow_webserver airflow dags trigger data_quality
    
} else {
    Write-Host "❌ Impossible de se connecter à Airflow" -ForegroundColor Red
}

# Vérifier MongoDB
if (Wait-ForService "http://localhost:8081" "Mongo Express") {
    Write-Host "`n💾 MongoDB est accessible via Mongo Express" -ForegroundColor Green
}

Write-Host "`n🎯 URLs de test:" -ForegroundColor Cyan
Write-Host "   • Airflow UI: http://localhost:8080 (admin/admin)" -ForegroundColor White
Write-Host "   • Mongo Express: http://localhost:8081" -ForegroundColor White

Write-Host "`n✅ Test terminé! Vérifiez les interfaces web pour voir les résultats." -ForegroundColor Green
