# Script de démarrage pour YouTube ELT Pipeline
# Usage: .\start-project.ps1

Write-Host "🎬 Démarrage du YouTube ELT Pipeline..." -ForegroundColor Cyan

# Vérifier que Docker est installé et en cours d'exécution
Write-Host "`n🔍 Vérification de Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "   ✅ Docker détecté: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Docker n'est pas installé ou n'est pas en cours d'exécution" -ForegroundColor Red
    Write-Host "   📥 Installez Docker Desktop: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Vérifier que docker-compose est disponible
try {
    $composeVersion = docker-compose --version
    Write-Host "   ✅ Docker Compose détecté: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Docker Compose n'est pas disponible" -ForegroundColor Red
    exit 1
}

# Vérifier la présence du fichier .env
Write-Host "`n🔧 Vérification de la configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "   ⚠️  Fichier .env non trouvé" -ForegroundColor Yellow
    Write-Host "   📝 Copie de .env.example vers .env..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "   ✅ Fichier .env créé" -ForegroundColor Green
    Write-Host "   📝 IMPORTANT: Éditez le fichier .env avec votre clé API YouTube!" -ForegroundColor Red
    Write-Host "   🔑 Obtenez votre clé API: https://developers.google.com/youtube/v3/getting-started" -ForegroundColor Yellow
} else {
    Write-Host "   ✅ Fichier .env trouvé" -ForegroundColor Green
}

# Démarrer l'infrastructure
Write-Host "`n🚀 Démarrage de l'infrastructure..." -ForegroundColor Yellow
Write-Host "   📦 Lancement des conteneurs Docker..." -ForegroundColor White

try {
    docker-compose -f docker-compose.final.yml up -d
    Write-Host "   ✅ Conteneurs démarrés avec succès!" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Erreur lors du démarrage des conteneurs" -ForegroundColor Red
    exit 1
}

# Attendre que les services soient prêts
Write-Host "`n⏳ Attente que les services soient prêts..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Vérifier l'état des services
Write-Host "`n📊 Vérification de l'état des services..." -ForegroundColor Yellow
$services = docker-compose -f docker-compose.final.yml ps --format "table {{.Name}}\t{{.Status}}"
Write-Host $services -ForegroundColor White

# Afficher les URLs d'accès
Write-Host "`n🌐 Services disponibles:" -ForegroundColor Cyan
Write-Host "   🖥️  Airflow Web UI:    http://localhost:8080 (admin/admin)" -ForegroundColor Green
Write-Host "   🗄️  MongoDB:           localhost:27017 (admin/password123)" -ForegroundColor Green
Write-Host "   📊 Mongo Express:      http://localhost:8081 (admin/admin123)" -ForegroundColor Green
Write-Host "   🚀 FastAPI:            http://localhost:8000" -ForegroundColor Green

Write-Host "`n📋 Prochaines étapes:" -ForegroundColor Cyan
Write-Host "   1. 🔑 Configurez votre clé API YouTube dans le fichier .env" -ForegroundColor Yellow
Write-Host "   2. 🌐 Accédez à Airflow: http://localhost:8080" -ForegroundColor Yellow
Write-Host "   3. ▶️  Activez et exécutez les DAGs dans l'interface Airflow" -ForegroundColor Yellow
Write-Host "   4. 📊 Surveillez l'exécution dans l'interface web" -ForegroundColor Yellow

Write-Host "`n🎉 YouTube ELT Pipeline est prêt!" -ForegroundColor Green
Write-Host "📖 Consultez le README.md pour plus d'informations" -ForegroundColor White
