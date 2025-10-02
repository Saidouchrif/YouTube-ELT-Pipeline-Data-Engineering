# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

## [1.1.0] - 2025-01-02

### ✅ Ajouté
- **README.md complet** avec documentation détaillée de l'architecture
- **Scripts de démarrage automatique** (`start-project.ps1`, `stop-project.ps1`)
- **requirements-ci.txt** pour les environnements CI/CD
- **Section dépannage** dans la documentation
- **Diagrammes d'architecture** avec Mermaid
- **Guide de contribution** détaillé

### 🔧 Corrigé
- **Problème Soda Core** : Migration vers `soda-core>=3.0.0`
- **Compatibilité CI/CD** : Résolution des conflits de versions
- **Configuration MongoDB** : Ajout de `auth_database: admin`
- **Workflow GitHub Actions** : Utilisation de `requirements-ci.txt`
- **Imports relatifs Airflow** : Correction des imports dans les plugins

### 🔄 Modifié
- **requirements.txt** : Versions flexibles pour compatibilité
- **soda_config.yml** : Configuration MongoDB mise à jour
- **checks_mongo.yml** : Simplification des règles de validation
- **Workflow CI** : Optimisation pour les tests

### 📚 Documentation
- **Architecture complète** : Diagrammes et explications détaillées
- **Guide d'installation** : Instructions pas-à-pas
- **Dépannage** : Solutions aux problèmes courants
- **Standards de code** : Guidelines pour les contributions

## [1.0.0] - 2025-01-01

### 🎉 Version Initiale
- **Pipeline ELT complet** pour données YouTube
- **4 DAGs Airflow** : extraction, transformation, qualité, pipeline intégré
- **3 collections MongoDB** : staging, core, history avec SCD2
- **Validation qualité** avec Soda Core
- **Infrastructure Docker** complète
- **Tests unitaires et d'intégration**
- **CI/CD avec GitHub Actions**

### 🏗️ Architecture
- **Apache Airflow 2.7.3** pour l'orchestration
- **MongoDB 7.0** pour le stockage
- **FastAPI** pour l'API de service
- **Docker Compose** pour l'infrastructure
- **Python 3.11** avec type hints

### 📊 Fonctionnalités
- **Extraction API YouTube v3** avec gestion des quotas
- **Transformation et nettoyage** des données
- **Historisation SCD2** pour le tracking des changements
- **Tests de qualité automatisés**
- **Monitoring et alertes**
- **Documentation complète**
