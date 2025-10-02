"""
Airflow DAG: data_validation_pipeline
- Exécuter la validation de qualité des données (complétude, cohérence, formats)
- Après validation réussie: lire les données transformées depuis MongoDB staging
- Sauvegarder les données validées dans la collection MongoDB core_data
- Logger toutes les étapes dans Airflow (succès, erreurs, nombre de lignes)
- Envoyer alertes si la validation échoue ou si la sauvegarde MongoDB échoue
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Dict, Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowFailException

from config.settings import config
from youtube_elt.db import get_collection
from youtube_elt.load import transform_and_upsert_core


DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def validate_data_quality(**context) -> Dict[str, Any]:
    """
    Valider la qualité des données dans la collection staging.
    
    Returns:
        Dict contenant les résultats de validation
    """
    print("🔍 === DÉBUT DE LA VALIDATION DE QUALITÉ DES DONNÉES ===")
    
    try:
        staging_collection = get_collection(config.STAGING_COLLECTION)
        
        # Compter les enregistrements
        total_records = staging_collection.count_documents({})
        print(f"📊 Total des enregistrements staging: {total_records}")
        
        if total_records == 0:
            raise AirflowFailException("❌ ÉCHEC: Aucun enregistrement trouvé dans staging")
        
        # Tests de complétude
        print("\n🔍 Tests de complétude:")
        required_fields = ['video_id', 'title', 'view_count', 'like_count']
        completeness_issues = []
        
        for field in required_fields:
            null_count = staging_collection.count_documents({field: None})
            empty_count = staging_collection.count_documents({field: ""})
            total_issues = null_count + empty_count
            
            if total_issues > 0:
                issue = f"{field}: {total_issues} valeurs manquantes"
                completeness_issues.append(issue)
                print(f"   ❌ {issue}")
            else:
                print(f"   ✅ {field}: Complet ({total_records} valeurs)")
        
        # Tests de cohérence
        print("\n🔍 Tests de cohérence:")
        consistency_issues = []
        
        # Vérifier view_count positif
        negative_views = staging_collection.count_documents({"view_count": {"$lt": 0}})
        if negative_views > 0:
            issue = f"view_count négatif: {negative_views} enregistrements"
            consistency_issues.append(issue)
            print(f"   ❌ {issue}")
        else:
            print("   ✅ view_count: Tous positifs")
        
        # Vérifier like_count positif
        negative_likes = staging_collection.count_documents({"like_count": {"$lt": 0}})
        if negative_likes > 0:
            issue = f"like_count négatif: {negative_likes} enregistrements"
            consistency_issues.append(issue)
            print(f"   ❌ {issue}")
        else:
            print("   ✅ like_count: Tous positifs")
        
        # Résumé de validation
        total_issues = len(completeness_issues) + len(consistency_issues)
        
        validation_result = {
            "status": "PASSED" if total_issues == 0 else "FAILED",
            "total_records": total_records,
            "completeness_issues": completeness_issues,
            "consistency_issues": consistency_issues,
            "total_issues": total_issues,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if total_issues == 0:
            print(f"\n🎉 VALIDATION RÉUSSIE: {total_records} enregistrements validés")
        else:
            print(f"\n⚠️ VALIDATION ÉCHOUÉE: {total_issues} problèmes détectés")
            for issue in completeness_issues + consistency_issues:
                print(f"   - {issue}")
            
            # Lever une exception pour arrêter le pipeline
            raise AirflowFailException(f"Validation échouée: {total_issues} problèmes détectés")
        
        # Stocker les résultats dans XCom
        context["ti"].xcom_push(key="validation_result", value=validation_result)
        
        print(f"📊 Statut de validation: {validation_result['status']}")
        return validation_result
        
    except AirflowFailException:
        raise
    except Exception as e:
        error_msg = f"Erreur lors de la validation: {str(e)}"
        print(f"❌ {error_msg}")
        raise AirflowFailException(error_msg)


def read_and_transform_staging_data(**context) -> Dict[str, Any]:
    """
    Lire les données validées depuis staging et les transformer.
    
    Returns:
        Dict contenant les statistiques de transformation
    """
    print("🔄 === LECTURE ET TRANSFORMATION DES DONNÉES STAGING ===")
    
    try:
        # Vérifier que la validation a réussi
        validation_result = context["ti"].xcom_pull(key="validation_result", task_ids="validate_quality")
        
        if not validation_result or validation_result.get("status") != "PASSED":
            raise AirflowFailException("❌ Validation préalable échouée, arrêt de la transformation")
        
        print(f"✅ Validation confirmée: {validation_result['total_records']} enregistrements validés")
        
        # Lire les données de staging
        staging_collection = get_collection(config.STAGING_COLLECTION)
        staging_records = list(staging_collection.find({}, {"_id": 0}))
        
        print(f"📖 Lecture de {len(staging_records)} enregistrements depuis staging")
        
        if not staging_records:
            raise AirflowFailException("❌ Aucune donnée trouvée dans staging")
        
        # Créer le dataset pour transformation
        dataset = {
            "channel_handle": config.YOUTUBE_CHANNEL_HANDLE,
            "extraction_date": datetime.utcnow().isoformat(),
            "total_videos": len(staging_records),
            "videos": staging_records
        }
        
        print(f"✅ Dataset créé avec {len(staging_records)} vidéos")
        
        # Stocker dans XCom pour la tâche suivante
        context["ti"].xcom_push(key="transformed_dataset", value=dataset)
        
        transform_result = {
            "records_read": len(staging_records),
            "dataset_created": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        print(f"📊 Transformation préparée: {transform_result['records_read']} enregistrements")
        return transform_result
        
    except AirflowFailException:
        raise
    except Exception as e:
        error_msg = f"Erreur lors de la lecture/transformation: {str(e)}"
        print(f"❌ {error_msg}")
        raise AirflowFailException(error_msg)


def save_validated_data_to_core(**context) -> Dict[str, Any]:
    """
    Sauvegarder les données validées dans la collection core_data.
    
    Returns:
        Dict contenant les statistiques de sauvegarde
    """
    print("💾 === SAUVEGARDE DES DONNÉES VALIDÉES DANS CORE ===")
    
    try:
        # Récupérer le dataset transformé
        dataset = context["ti"].xcom_pull(key="transformed_dataset", task_ids="read_transform_staging")
        
        if not dataset:
            raise AirflowFailException("❌ Aucun dataset trouvé pour la sauvegarde")
        
        print(f"📥 Dataset reçu avec {dataset['total_videos']} vidéos")
        
        # Sauvegarder dans core avec transformation
        records_saved = transform_and_upsert_core(dataset)
        
        print(f"✅ Sauvegarde réussie: {records_saved} enregistrements upsertés dans core")
        
        # Vérifier la sauvegarde
        core_collection = get_collection(config.CORE_COLLECTION)
        core_count = core_collection.count_documents({})
        
        print(f"📊 Collection core maintenant: {core_count} enregistrements au total")
        
        # Statistiques finales
        save_result = {
            "records_processed": dataset['total_videos'],
            "records_saved": records_saved,
            "total_core_records": core_count,
            "status": "SUCCESS",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        print(f"🎉 SAUVEGARDE TERMINÉE AVEC SUCCÈS")
        print(f"   - Enregistrements traités: {save_result['records_processed']}")
        print(f"   - Enregistrements sauvegardés: {save_result['records_saved']}")
        print(f"   - Total en base core: {save_result['total_core_records']}")
        
        return save_result
        
    except AirflowFailException:
        raise
    except Exception as e:
        error_msg = f"Erreur lors de la sauvegarde: {str(e)}"
        print(f"❌ {error_msg}")
        raise AirflowFailException(error_msg)


def generate_pipeline_report(**context) -> Dict[str, Any]:
    """
    Générer un rapport final du pipeline avec toutes les statistiques.
    
    Returns:
        Dict contenant le rapport complet
    """
    print("📋 === GÉNÉRATION DU RAPPORT FINAL ===")
    
    try:
        # Récupérer les résultats de toutes les tâches
        validation_result = context["ti"].xcom_pull(key="validation_result", task_ids="validate_quality")
        transform_result = context["ti"].xcom_pull(task_ids="read_transform_staging")
        save_result = context["ti"].xcom_pull(task_ids="save_to_core")
        
        # Générer le rapport final
        pipeline_report = {
            "pipeline_name": "data_validation_pipeline",
            "execution_date": context["ds"],
            "timestamp": datetime.utcnow().isoformat(),
            "status": "SUCCESS",
            "validation": validation_result or {"status": "ERROR"},
            "transformation": transform_result or {"status": "ERROR"},
            "save_operation": save_result or {"status": "ERROR"},
            "summary": {
                "total_records_validated": validation_result.get("total_records", 0) if validation_result else 0,
                "total_records_saved": save_result.get("records_saved", 0) if save_result else 0,
                "pipeline_duration_seconds": (datetime.utcnow() - datetime.fromisoformat(context["ts"])).total_seconds()
            }
        }
        
        print("📊 === RAPPORT FINAL DU PIPELINE ===")
        print(f"   🎯 Statut global: {pipeline_report['status']}")
        print(f"   📈 Enregistrements validés: {pipeline_report['summary']['total_records_validated']}")
        print(f"   💾 Enregistrements sauvegardés: {pipeline_report['summary']['total_records_saved']}")
        print(f"   ⏱️  Durée d'exécution: {pipeline_report['summary']['pipeline_duration_seconds']:.2f}s")
        print(f"   📅 Timestamp: {pipeline_report['timestamp']}")
        
        return pipeline_report
        
    except Exception as e:
        error_msg = f"Erreur lors de la génération du rapport: {str(e)}"
        print(f"❌ {error_msg}")
        return {"status": "ERROR", "error": error_msg}


def send_alert_on_failure(**context) -> None:
    """
    Envoyer une alerte en cas d'échec du pipeline.
    """
    print("🚨 === ALERTE: ÉCHEC DU PIPELINE ===")
    
    try:
        # Récupérer les informations d'erreur
        task_instance = context["task_instance"]
        dag_run = context["dag_run"]
        
        alert_info = {
            "pipeline": "data_validation_pipeline",
            "status": "FAILED",
            "failed_task": task_instance.task_id,
            "execution_date": context["ds"],
            "timestamp": datetime.utcnow().isoformat(),
            "dag_run_id": dag_run.run_id
        }
        
        print(f"🚨 ALERTE GÉNÉRÉE:")
        print(f"   - Pipeline: {alert_info['pipeline']}")
        print(f"   - Tâche échouée: {alert_info['failed_task']}")
        print(f"   - Date d'exécution: {alert_info['execution_date']}")
        print(f"   - ID de run: {alert_info['dag_run_id']}")
        
        # Ici on pourrait ajouter l'envoi d'email, Slack, etc.
        # Pour l'instant, on log l'alerte
        print("📧 Alerte loggée (intégration email/Slack à implémenter)")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi d'alerte: {str(e)}")


# Définition du DAG
with DAG(
    dag_id="data_validation_pipeline",
    description="Pipeline intégré: validation qualité → transformation → sauvegarde core avec alertes",
    default_args=DEFAULT_ARGS,
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["youtube", "validation", "pipeline", "core"],
) as dag:

    # Tâche 1: Validation de la qualité des données
    validate_task = PythonOperator(
        task_id="validate_quality",
        python_callable=validate_data_quality,
        provide_context=True,
    )

    # Tâche 2: Lecture et transformation des données staging
    transform_task = PythonOperator(
        task_id="read_transform_staging",
        python_callable=read_and_transform_staging_data,
        provide_context=True,
    )

    # Tâche 3: Sauvegarde dans core_data
    save_task = PythonOperator(
        task_id="save_to_core",
        python_callable=save_validated_data_to_core,
        provide_context=True,
    )

    # Tâche 4: Génération du rapport final
    report_task = PythonOperator(
        task_id="generate_report",
        python_callable=generate_pipeline_report,
        provide_context=True,
        trigger_rule="all_done",  # S'exécute même si les tâches précédentes échouent
    )

    # Tâche 5: Alerte en cas d'échec
    alert_task = PythonOperator(
        task_id="send_failure_alert",
        python_callable=send_alert_on_failure,
        provide_context=True,
        trigger_rule="one_failed",  # S'exécute seulement si une tâche échoue
    )

    # Définition des dépendances
    validate_task >> transform_task >> save_task >> report_task
    [validate_task, transform_task, save_task] >> alert_task
