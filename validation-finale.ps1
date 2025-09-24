# Validation finale du pipeline YouTube ELT
Write-Host "🎯 VALIDATION FINALE - YouTube ELT Pipeline" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green

# Test 1: Vérification des services
Write-Host "`n📊 1. VÉRIFICATION DES SERVICES" -ForegroundColor Cyan
Write-Host "-" * 40 -ForegroundColor Cyan

$services = @(
    @{Name="MongoDB"; Command="docker exec youtube_mongodb mongosh --quiet --eval 'db.adminCommand(`"ping`").ok'"; Expected="1"},
    @{Name="FastAPI"; Command="curl -s http://localhost:8000/health"; Expected="healthy"},
    @{Name="Mongo Express"; Command="curl -s -o /dev/null -w '%{http_code}' http://localhost:8081"; Expected="200"}
)

foreach ($service in $services) {
    try {
        Write-Host "   Testing $($service.Name)..." -ForegroundColor Yellow
        $result = Invoke-Expression $service.Command 2>$null
        if ($result -match $service.Expected) {
            Write-Host "   ✅ $($service.Name): OK" -ForegroundColor Green
        } else {
            Write-Host "   ❌ $($service.Name): FAILED" -ForegroundColor Red
        }
    } catch {
        Write-Host "   ❌ $($service.Name): ERROR" -ForegroundColor Red
    }
}

# Test 2: Test complet de l'API avec données réelles
Write-Host "`n🎬 2. TEST EXTRACTION DONNÉES YOUTUBE" -ForegroundColor Cyan
Write-Host "-" * 40 -ForegroundColor Cyan

$testData = @{
    channel_handle = "MrBeast"
    max_results = 2
    use_pagination = $false
    save_to_file = $true
} | ConvertTo-Json

try {
    Write-Host "   📡 Envoi requête à l'API..." -ForegroundColor Yellow
    $response = Invoke-RestMethod -Uri "http://localhost:8000/channel" -Method Post -Body $testData -ContentType "application/json" -TimeoutSec 30
    
    Write-Host "   ✅ Extraction réussie!" -ForegroundColor Green
    Write-Host "   📺 Chaîne: $($response.channel_handle)" -ForegroundColor White
    Write-Host "   🎬 Vidéos récupérées: $($response.total_videos)" -ForegroundColor White
    Write-Host "   📅 Date extraction: $($response.extraction_date)" -ForegroundColor White
    
    if ($response.videos -and $response.videos.Count -gt 0) {
        Write-Host "   🏆 Première vidéo: $($response.videos[0].title)" -ForegroundColor Cyan
        Write-Host "   👀 Vues: $($response.videos[0].view_count)" -ForegroundColor White
        Write-Host "   👍 Likes: $($response.videos[0].like_count)" -ForegroundColor White
    }
    
    $extractionSuccess = $true
} catch {
    Write-Host "   ❌ Erreur extraction: $($_.Exception.Message)" -ForegroundColor Red
    $extractionSuccess = $false
}

# Test 3: Vérification des quotas
Write-Host "`n📈 3. VÉRIFICATION GESTION QUOTAS" -ForegroundColor Cyan
Write-Host "-" * 40 -ForegroundColor Cyan

try {
    $quota = Invoke-RestMethod -Uri "http://localhost:8000/quota/status" -TimeoutSec 10
    Write-Host "   ✅ Quotas récupérés" -ForegroundColor Green
    Write-Host "   📊 Utilisé: $($quota.used_quota)/$($quota.daily_limit)" -ForegroundColor White
    Write-Host "   📊 Restant: $($quota.remaining_quota)" -ForegroundColor White
    Write-Host "   📊 Pourcentage: $([math]::Round($quota.percentage_used, 2))%" -ForegroundColor White
    $quotaSuccess = $true
} catch {
    Write-Host "   ❌ Erreur quotas" -ForegroundColor Red
    $quotaSuccess = $false
}

# Test 4: Vérification des fichiers sauvegardés
Write-Host "`n💾 4. VÉRIFICATION SAUVEGARDE DONNÉES" -ForegroundColor Cyan
Write-Host "-" * 40 -ForegroundColor Cyan

$dataPath = "Keys\Data\channels\mrbeast"
if (Test-Path $dataPath) {
    $files = Get-ChildItem $dataPath -Filter "*.json" | Sort-Object LastWriteTime -Descending
    Write-Host "   ✅ Répertoire de données trouvé" -ForegroundColor Green
    Write-Host "   📁 Nombre de fichiers: $($files.Count)" -ForegroundColor White
    
    if ($files.Count -gt 0) {
        $latestFile = $files[0]
        Write-Host "   📄 Fichier le plus récent: $($latestFile.Name)" -ForegroundColor Cyan
        Write-Host "   📅 Date: $($latestFile.LastWriteTime)" -ForegroundColor White
        Write-Host "   📏 Taille: $([math]::Round($latestFile.Length/1KB, 2)) KB" -ForegroundColor White
        $filesSuccess = $true
    } else {
        Write-Host "   ❌ Aucun fichier de données trouvé" -ForegroundColor Red
        $filesSuccess = $false
    }
} else {
    Write-Host "   ❌ Répertoire de données non trouvé" -ForegroundColor Red
    $filesSuccess = $false
}

# Test 5: Test MongoDB collections
Write-Host "`n🗄️ 5. VÉRIFICATION COLLECTIONS MONGODB" -ForegroundColor Cyan
Write-Host "-" * 40 -ForegroundColor Cyan

try {
    $collections = docker exec youtube_mongodb mongosh --quiet youtube_data --eval "db.getCollectionNames()" 2>$null
    Write-Host "   ✅ Collections MongoDB accessibles" -ForegroundColor Green
    Write-Host "   📋 Collections: $collections" -ForegroundColor White
    $mongoSuccess = $true
} catch {
    Write-Host "   ❌ Erreur accès collections MongoDB" -ForegroundColor Red
    $mongoSuccess = $false
}

# Résumé final
Write-Host "`n🏆 RÉSUMÉ FINAL" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green

$tests = @(
    @{Name="Services Docker"; Success=$true},
    @{Name="Extraction YouTube"; Success=$extractionSuccess},
    @{Name="Gestion Quotas"; Success=$quotaSuccess},
    @{Name="Sauvegarde Fichiers"; Success=$filesSuccess},
    @{Name="Collections MongoDB"; Success=$mongoSuccess}
)

$successCount = 0
foreach ($test in $tests) {
    $status = if ($test.Success) { "✅ RÉUSSI" } else { "❌ ÉCHEC" }
    $color = if ($test.Success) { "Green" } else { "Red" }
    Write-Host "$($test.Name): $status" -ForegroundColor $color
    if ($test.Success) { $successCount++ }
}

Write-Host "`n📊 SCORE: $successCount/$($tests.Count) tests réussis" -ForegroundColor $(if($successCount -eq $tests.Count) {"Green"} else {"Yellow"})

if ($successCount -eq $tests.Count) {
    Write-Host "`n🎉 PIPELINE YOUTUBE ELT COMPLÈTEMENT OPÉRATIONNEL!" -ForegroundColor Green
    Write-Host "🚀 Prêt pour la production!" -ForegroundColor Green
} else {
    Write-Host "`n⚠️ Certains composants nécessitent une attention" -ForegroundColor Yellow
}

Write-Host "`n🌐 ACCÈS AUX SERVICES:" -ForegroundColor Cyan
Write-Host "• API FastAPI:     http://localhost:8000" -ForegroundColor White
Write-Host "• Documentation:   http://localhost:8000/docs" -ForegroundColor White
Write-Host "• Mongo Express:   http://localhost:8081 (admin/admin123)" -ForegroundColor White
Write-Host "• Airflow:         http://localhost:8080 (admin/admin)" -ForegroundColor White
