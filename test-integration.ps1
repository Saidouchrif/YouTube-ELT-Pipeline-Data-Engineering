# Test d'intégration complet du pipeline YouTube ELT
Write-Host "🔄 Test d'Intégration Complet - YouTube ELT Pipeline" -ForegroundColor Green

# Fonction pour tester la connectivité MongoDB
function Test-MongoDB {
    Write-Host "`n📊 Test de connectivité MongoDB..." -ForegroundColor Cyan
    try {
        $result = docker exec youtube_mongodb mongosh --quiet --eval "db.adminCommand('ping').ok"
        if ($result -eq "1") {
            Write-Host "   ✅ MongoDB connecté et opérationnel" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host "   ❌ Erreur MongoDB: $($_.Exception.Message)" -ForegroundColor Red
    }
    return $false
}

# Fonction pour tester l'API et récupérer des données
function Test-APIAndData {
    Write-Host "`n🎯 Test de récupération de données via API..." -ForegroundColor Cyan
    try {
        $body = @{
            channel_handle = "MrBeast"
            max_results = 3
            use_pagination = $false
            save_to_file = $true
        } | ConvertTo-Json
        
        Write-Host "   📡 Envoi de la requête à l'API..." -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri "http://localhost:8000/channel" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 45
        
        Write-Host "   ✅ Données récupérées avec succès!" -ForegroundColor Green
        Write-Host "   📺 Chaîne: $($response.channel_handle)" -ForegroundColor White
        Write-Host "   🎬 Nombre de vidéos: $($response.total_videos)" -ForegroundColor White
        Write-Host "   📅 Date d'extraction: $($response.extraction_date)" -ForegroundColor White
        
        if ($response.videos -and $response.videos.Count -gt 0) {
            Write-Host "   🏆 Première vidéo: $($response.videos[0].title)" -ForegroundColor White
            Write-Host "   👀 Vues: $($response.videos[0].view_count)" -ForegroundColor White
        }
        
        if ($response._saved_files) {
            Write-Host "   💾 Fichiers sauvegardés: $($response._saved_files.Count)" -ForegroundColor Green
        }
        
        return $response
    } catch {
        Write-Host "   ❌ Erreur API: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# Fonction pour vérifier les collections MongoDB
function Test-MongoCollections {
    Write-Host "`n🗄️ Vérification des collections MongoDB..." -ForegroundColor Cyan
    try {
        # Lister les collections
        $collections = docker exec youtube_mongodb mongosh --quiet youtube_data --eval "db.getCollectionNames()" 2>$null
        Write-Host "   📋 Collections disponibles: $collections" -ForegroundColor White
        
        # Compter les documents dans staging_data
        $stagingCount = docker exec youtube_mongodb mongosh --quiet youtube_data --eval "db.staging_data.countDocuments({})" 2>$null
        Write-Host "   📊 Documents dans staging_data: $stagingCount" -ForegroundColor White
        
        # Compter les documents dans core_data
        $coreCount = docker exec youtube_mongodb mongosh --quiet youtube_data --eval "db.core_data.countDocuments({})" 2>$null
        Write-Host "   📊 Documents dans core_data: $coreCount" -ForegroundColor White
        
        return $true
    } catch {
        Write-Host "   ❌ Erreur lors de la vérification des collections: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Fonction pour tester les quotas
function Test-Quotas {
    Write-Host "`n📈 Test de gestion des quotas..." -ForegroundColor Cyan
    try {
        $quota = Invoke-RestMethod -Uri "http://localhost:8000/quota/status" -Method Get -TimeoutSec 10
        Write-Host "   ✅ Quotas récupérés" -ForegroundColor Green
        Write-Host "   📊 Quota utilisé: $($quota.used_quota)/$($quota.daily_limit)" -ForegroundColor White
        Write-Host "   📊 Quota restant: $($quota.remaining_quota)" -ForegroundColor White
        Write-Host "   📊 Pourcentage utilisé: $([math]::Round($quota.percentage_used, 2))%" -ForegroundColor White
        return $true
    } catch {
        Write-Host "   ❌ Erreur quotas: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Exécution des tests
Write-Host "🚀 Démarrage des tests d'intégration..." -ForegroundColor Yellow

# Test 1: MongoDB
$mongoOK = Test-MongoDB

# Test 2: Quotas
$quotaOK = Test-Quotas

# Test 3: API et récupération de données
$apiData = Test-APIAndData

# Test 4: Collections MongoDB
$collectionsOK = Test-MongoCollections

# Résumé final
Write-Host "`n📋 RÉSUMÉ DES TESTS" -ForegroundColor Green
Write-Host "===================" -ForegroundColor Green
Write-Host "MongoDB:           $(if($mongoOK) {'✅ OK'} else {'❌ ÉCHEC'})" -ForegroundColor $(if($mongoOK) {'Green'} else {'Red'})
Write-Host "Gestion Quotas:    $(if($quotaOK) {'✅ OK'} else {'❌ ÉCHEC'})" -ForegroundColor $(if($quotaOK) {'Green'} else {'Red'})
Write-Host "API YouTube:       $(if($apiData) {'✅ OK'} else {'❌ ÉCHEC'})" -ForegroundColor $(if($apiData) {'Green'} else {'Red'})
Write-Host "Collections DB:    $(if($collectionsOK) {'✅ OK'} else {'❌ ÉCHEC'})" -ForegroundColor $(if($collectionsOK) {'Green'} else {'Red'})

if ($mongoOK -and $quotaOK -and $apiData -and $collectionsOK) {
    Write-Host "`n🎉 TOUS LES TESTS RÉUSSIS!" -ForegroundColor Green
    Write-Host "Le pipeline YouTube ELT est opérationnel!" -ForegroundColor Green
} else {
    Write-Host "`n⚠️ Certains tests ont échoué" -ForegroundColor Yellow
    Write-Host "Vérifiez les logs des services concernés" -ForegroundColor Yellow
}

Write-Host "`n🌐 Services disponibles:" -ForegroundColor Cyan
Write-Host "• API FastAPI:     http://localhost:8000" -ForegroundColor White
Write-Host "• Mongo Express:   http://localhost:8081 (admin/admin123)" -ForegroundColor White
Write-Host "• Airflow:         http://localhost:8080 (admin/admin) - En cours de démarrage" -ForegroundColor White
