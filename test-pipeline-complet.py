#!/usr/bin/env python3
"""
Test d'intégration complète du pipeline YouTube ELT
Simule le processus complet : Extract -> Load -> Transform
"""

import sys
import os
import json
import datetime
from pathlib import Path

# Ajouter les chemins nécessaires
sys.path.append(str(Path(__file__).parent / "plugins"))
sys.path.append(str(Path(__file__).parent / "config"))

try:
    from plugins.youtube_elt.extract import YouTubeExtractor
    from plugins.youtube_elt.load import load_staging_from_file, transform_and_upsert_core, upsert_history
    from plugins.youtube_elt.db import get_mongo_client, get_database, ensure_indexes
    from config.settings import Config
    
    print("✅ Tous les modules importés avec succès")
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    sys.exit(1)

def test_extraction():
    """Test de l'extraction de données YouTube"""
    print("\n🔍 ÉTAPE 1: EXTRACTION")
    print("=" * 50)
    
    try:
        # Initialiser la configuration
        config = Config()
        
        # Créer l'extracteur
        extractor = YouTubeExtractor(config.YOUTUBE_API_KEY)
        
        # Extraire les données
        print(f"📡 Extraction des données pour {config.YOUTUBE_CHANNEL_HANDLE}...")
        channel_videos = extractor.extract_channel_videos(
            config.YOUTUBE_CHANNEL_HANDLE, 
            max_results=3
        )
        
        if channel_videos and 'videos' in channel_videos:
            print(f"✅ Extraction réussie: {len(channel_videos['videos'])} vidéos")
            print(f"📺 Première vidéo: {channel_videos['videos'][0]['title']}")
            
            # Sauvegarder les données
            staging_path = Path("data/staging")
            staging_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"youtube_data_{config.YOUTUBE_CHANNEL_HANDLE}_{timestamp}.json"
            filepath = staging_path / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(channel_videos, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Données sauvegardées: {filepath}")
            return str(filepath)
        else:
            print("❌ Aucune donnée extraite")
            return None
            
    except Exception as e:
        print(f"❌ Erreur lors de l'extraction: {e}")
        return None

def test_load_and_transform(staging_file):
    """Test du chargement et de la transformation"""
    print("\n📥 ÉTAPE 2: LOAD & TRANSFORM")
    print("=" * 50)
    
    try:
        # Configurer MongoDB pour les tests
        os.environ["USE_MOCK_DB"] = "false"  # Utiliser la vraie DB
        
        # Obtenir la connexion MongoDB
        client = get_mongo_client()
        db = get_database()
        
        print("✅ Connexion MongoDB établie")
        
        # Assurer les index
        ensure_indexes()
        print("✅ Index MongoDB vérifiés")
        
        # Charger les données dans staging
        print(f"📂 Chargement du fichier: {staging_file}")
        staging_result = load_staging_from_file(staging_file)
        
        if staging_result:
            print(f"✅ Chargement staging réussi: {staging_result['inserted_count']} documents")
            
            # Transformer et charger dans core
            print("🔄 Transformation et chargement dans core_data...")
            core_result = transform_and_upsert_core()
            
            if core_result:
                print(f"✅ Transformation réussie: {core_result['upserted_count']} documents")
                
                # Historiser les données
                print("📚 Historisation des données...")
                history_result = upsert_history()
                
                if history_result:
                    print(f"✅ Historisation réussie: {history_result['upserted_count']} documents")
                    return True
        
        return False
        
    except Exception as e:
        print(f"❌ Erreur lors du load/transform: {e}")
        return False

def test_data_verification():
    """Vérification des données dans MongoDB"""
    print("\n🔍 ÉTAPE 3: VÉRIFICATION DES DONNÉES")
    print("=" * 50)
    
    try:
        client = get_mongo_client()
        db = get_database()
        
        # Compter les documents dans chaque collection
        collections = ['staging_data', 'core_data', 'history_data']
        
        for collection_name in collections:
            collection = db[collection_name]
            count = collection.count_documents({})
            print(f"📊 {collection_name}: {count} documents")
            
            if count > 0:
                # Afficher un exemple de document
                sample = collection.find_one()
                if sample:
                    print(f"   📄 Exemple: {sample.get('title', sample.get('video_id', 'N/A'))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False

def main():
    """Fonction principale du test"""
    print("🚀 TEST D'INTÉGRATION COMPLÈTE - YouTube ELT Pipeline")
    print("=" * 60)
    
    # Test d'extraction
    staging_file = test_extraction()
    
    if not staging_file:
        print("❌ Test d'extraction échoué, arrêt du pipeline")
        return False
    
    # Test de chargement et transformation
    load_success = test_load_and_transform(staging_file)
    
    if not load_success:
        print("❌ Test de chargement/transformation échoué")
        return False
    
    # Vérification des données
    verification_success = test_data_verification()
    
    if verification_success:
        print("\n🎉 PIPELINE ELT COMPLET TESTÉ AVEC SUCCÈS!")
        print("✅ Extraction: OK")
        print("✅ Load: OK") 
        print("✅ Transform: OK")
        print("✅ Vérification: OK")
        return True
    else:
        print("\n❌ Échec de la vérification finale")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
