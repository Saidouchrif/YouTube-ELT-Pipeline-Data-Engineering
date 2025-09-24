# Script de test pour l'API FastAPI
Write-Host "🧪 Test de l'API FastAPI YouTube ELT Pipeline" -ForegroundColor Green

# Test 1: Health Check
Write-Host "`n1. Test Health Check..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 10
    Write-Host "   ✅ Health Check OK" -ForegroundColor Green
    Write-Host "   Status: $($health.status)" -ForegroundColor White
    Write-Host "   Service: $($health.service)" -ForegroundColor White
} catch {
    Write-Host "   ❌ Health Check échoué: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Root Endpoint
Write-Host "`n2. Test Root Endpoint..." -ForegroundColor Cyan
try {
    $root = Invoke-RestMethod -Uri "http://localhost:8000" -Method Get -TimeoutSec 10
    Write-Host "   ✅ Root Endpoint OK" -ForegroundColor Green
    Write-Host "   Message: $($root.message)" -ForegroundColor White
} catch {
    Write-Host "   ❌ Root Endpoint échoué: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Quota Status
Write-Host "`n3. Test Quota Status..." -ForegroundColor Cyan
try {
    $quota = Invoke-RestMethod -Uri "http://localhost:8000/quota/status" -Method Get -TimeoutSec 10
    Write-Host "   ✅ Quota Status OK" -ForegroundColor Green
    Write-Host "   Quota utilisé: $($quota.used_quota)/$($quota.daily_limit)" -ForegroundColor White
} catch {
    Write-Host "   ❌ Quota Status échoué: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Channel Data (version simple)
Write-Host "`n4. Test Channel Data..." -ForegroundColor Cyan
try {
    $body = @{
        channel_handle = "MrBeast"
        max_results = 2
        use_pagination = $false
        save_to_file = $false
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "http://localhost:8000/channel" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30
    Write-Host "   ✅ Channel Data OK" -ForegroundColor Green
    Write-Host "   Chaîne: $($response.channel_handle)" -ForegroundColor White
    Write-Host "   Nombre de vidéos: $($response.total_videos)" -ForegroundColor White
    if ($response.videos -and $response.videos.Count -gt 0) {
        Write-Host "   Première vidéo: $($response.videos[0].title)" -ForegroundColor White
    }
} catch {
    Write-Host "   ❌ Channel Data échoué: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎯 URLs d'accès:" -ForegroundColor Cyan
Write-Host "   • API FastAPI: http://localhost:8000" -ForegroundColor White
Write-Host "   • Mongo Express: http://localhost:8081 (admin/admin123)" -ForegroundColor White
Write-Host "   • Airflow: http://localhost:8080 (admin/admin)" -ForegroundColor White
Write-Host "   • MongoDB: mongodb://admin:password123@localhost:27017" -ForegroundColor White
