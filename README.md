# YouTube ELT Pipeline (Airflow + MongoDB)

Pipeline ELT complet pour extraire les données YouTube de la chaîne MrBeast, transformer et charger dans MongoDB, avec validation qualité via Soda Core, orchestré par Apache Airflow (Astro CLI) et packagé avec Docker.

## Architecture

- **Airflow DAGs** (`dags/`)
  - `produce_JSON.py`: Extraction API YouTube -> JSON horodatés dans `/data/staging/`
  - `update_db.py`: Chargement JSON -> `staging_data`, transformation -> `core_data`, historisation -> `history_data`
  - `data_quality.py`: Exécution des checks Soda Core sur MongoDB
- **Modules réutilisables** (`plugins/youtube_elt/`)
  - `extract.py`, `transform.py`, `load.py`, `db.py`
- **Configuration** (`config/`)
  - `settings.py` lit les variables depuis Airflow Variables (si dispo) ou `.env` / env
  - `soda_config.yml` + `soda/checks/checks_mongo.yml`
- **Données**
  - Exemple JSON: `data/staging/youtube_data_MrBeast_sample.json`
- **MongoDB**
  - `mongodb-init/init.js` pour créer collections et index
- **Tests** (`tests/`)
  - >20 tests avec `pytest` et `mongomock`

## Prérequis

- Docker + Docker Compose
- Astro CLI ([docs](https://docs.astronomer.io/astro/cli/install))
- Clé API YouTube Data v3

## Variables et secrets

Vous pouvez définir les secrets de 2 façons :

1. Airflow Variables (recommandé en prod)
   - `YOUTUBE_API_KEY`
   - `YOUTUBE_CHANNEL_HANDLE` (ex: `MrBeast`)
   - `YOUTUBE_MAX_RESULTS` (ex: `50`)
   - `YOUTUBE_QUOTA_LIMIT` (ex: `10000`)
2. Fichier `.env` (copier `.env.example` en `.env` et ajuster)

Le module `config/settings.py` lit d'abord les Variables Airflow, puis l'environnement.

## Lancer en local (Astro + Docker)

1. Construire et démarrer l'environnement

```bash
astro dev start
```

Cela démarre Airflow et crée le réseau Docker `airflow`. Ensuite démarrez MongoDB et Mongo Express :

```bash
docker compose -f docker-compose.override.yml up -d
```

2. Accéder aux interfaces

- Airflow: http://localhost:8080 (user/pass par défaut: `admin`/`admin` via Astro)
- Mongo Express: http://localhost:8081

3. Créer la Variable Airflow `YOUTUBE_API_KEY`

Airflow UI -> Admin -> Variables -> Add a new record -> Key: `YOUTUBE_API_KEY` -> Value: votre clé.

4. Exécuter les DAGs

- `produce_JSON`: génère un JSON dans `/data/staging/` (dans le conteneur Airflow)
- `update_db`: charge le dernier JSON -> MongoDB (`staging_data`, `core_data`, `history_data`)
- `data_quality`: exécute Soda Core et échoue si les règles ne passent pas

## Dossiers de données

- `DATA_STAGING_PATH` par défaut `/data/staging/`. Assurez-vous que ce dossier existe dans le conteneur Airflow (créé automatiquement par le code d'extraction si absent). Vous pouvez aussi monter un volume si besoin.

## Tests

Exécuter la suite de tests (utilise `mongomock` en mémoire) :

```bash
pip install -r requirements.txt
pytest -q --maxfail=1 --disable-warnings
```

## CI/CD (GitHub Actions)

Un workflow `ci.yml` exécute lint et tests à chaque push/PR.

## Modèle de données MongoDB

- `staging_data`: données brutes (clé `video_id` unique)
- `core_data`: données transformées et standardisées
- `history_data`: historisation de type SCD2

Champs d'historisation: `valid_from`, `valid_to`, `created_at`, `updated_at`

## Qualité des données (Soda Core)

Fichier `soda/checks/checks_mongo.yml` avec règles :

- **Présence**: `row_count > 0` sur `staging_data` et `core_data`
- **Unicité**: `duplicate_count(video_id) = 0` sur `core_data`
- **Formats**: compteurs non négatifs, colonnes requises en `history_data`

## Notes sur la consommation de quota YouTube

Le module `extract.py` implémente une estimation simple de coût et du retry/backoff. Ajustez `YOUTUBE_MAX_RESULTS` et la planification des DAGs selon vos quotas.

## Arborescence

```
├── dags/
├── plugins/
│   └── youtube_elt/ (extract, transform, load, db)
├── config/ (settings, soda)
├── soda/checks/
├── data/staging/
├── mongodb-init/
├── tests/
├── Dockerfile
├── astro.yaml
├── docker-compose.override.yml
├── requirements.txt
└── README.md
```

## Licence

MIT
