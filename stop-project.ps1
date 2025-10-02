# Script d'arrêt pour YouTube ELT Pipeline
# Usage: .\stop-project.ps1

Write-Host "🛑 Arrêt du YouTube ELT Pipeline..." -ForegroundColor Cyan

# Arrêter les conteneurs
Write-Host "`n📦 Arrêt des conteneurs Docker..." -ForegroundColor Yellow
try {
    docker-compose -f docker-compose.final.yml down
    Write-Host "   ✅ Conteneurs arrêtés avec succès!" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Erreur lors de l'arrêt des conteneurs" -ForegroundColor Red
}

# Option pour nettoyer les volumes (données)
$cleanup = Read-Host "`n🗑️  Voulez-vous supprimer les données (volumes Docker)? (y/N)"
if ($cleanup -eq "y" -or $cleanup -eq "Y") {
    Write-Host "   🗑️  Suppression des volumes..." -ForegroundColor Yellow
    try {
        docker-compose -f docker-compose.final.yml down -v
        Write-Host "   ✅ Volumes supprimés!" -ForegroundColor Green
    } catch {
        Write-Host "   ❌ Erreur lors de la suppression des volumes" -ForegroundColor Red
    }
} else {
    Write-Host "   📊 Données conservées" -ForegroundColor Green
}

Write-Host "`n✅ YouTube ELT Pipeline arrêté!" -ForegroundColor Green
