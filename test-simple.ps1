Write-Host "🧪 Test Simple du Pipeline" -ForegroundColor Green

# Test API Health
Write-Host "`n1. Test API Health..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 10
    Write-Host "   ✅ API Health: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ API Health failed" -ForegroundColor Red
}

# Test MongoDB
Write-Host "`n2. Test MongoDB..." -ForegroundColor Cyan
try {
    $result = docker exec youtube_mongodb mongosh --quiet --eval "db.adminCommand('ping').ok"
    if ($result -match "1") {
        Write-Host "   ✅ MongoDB: Connected" -ForegroundColor Green
    }
} catch {
    Write-Host "   ❌ MongoDB failed" -ForegroundColor Red
}

# Test API Channel Data
Write-Host "`n3. Test Channel Data..." -ForegroundColor Cyan
$jsonBody = @"
{
    "channel_handle": "MrBeast",
    "max_results": 2,
    "use_pagination": false,
    "save_to_file": true
}
"@

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/channel" -Method Post -Body $jsonBody -ContentType "application/json" -TimeoutSec 30
    Write-Host "   ✅ Channel Data Retrieved!" -ForegroundColor Green
    Write-Host "   📺 Channel: $($response.channel_handle)" -ForegroundColor White
    Write-Host "   🎬 Videos: $($response.total_videos)" -ForegroundColor White
    if ($response.videos -and $response.videos.Count -gt 0) {
        Write-Host "   🏆 First Video: $($response.videos[0].title)" -ForegroundColor Cyan
    }
} catch {
    Write-Host "   ❌ Channel Data failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎯 Services Status:" -ForegroundColor Green
Write-Host "✅ FastAPI:      http://localhost:8000" -ForegroundColor White
Write-Host "✅ MongoDB:      Port 27017" -ForegroundColor White  
Write-Host "✅ Mongo Express: http://localhost:8081" -ForegroundColor White
Write-Host "⏳ Airflow:      http://localhost:8080 (starting...)" -ForegroundColor Yellow
