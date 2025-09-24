"""
Airflow DAG: update_db
- Load latest staging JSON into MongoDB staging.
- Transform and upsert into core and history collections.
"""
from __future__ import annotations

import glob
import os
from datetime import datetime, timedelta
from pathlib import Path
import json

from airflow import DAG
from airflow.operators.python import PythonOperator

from config.settings import config
from plugins.youtube_elt.load import load_staging_from_file, transform_and_upsert_core, upsert_history


DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def find_latest_staging_file() -> str:
    pattern = os.path.join(config.DATA_STAGING_PATH, f"youtube_data_{config.YOUTUBE_CHANNEL_HANDLE}_*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No staging files found in {config.DATA_STAGING_PATH}")
    return files[-1]


def load_to_staging(**context):
    file_path = context.get("ti").xcom_pull(dag_id="produce_JSON", task_ids="extract_youtube_data", key="staging_file_path")
    if not file_path:
        file_path = find_latest_staging_file()
    count = load_staging_from_file(file_path)
    return {"file": file_path, "staging_upserts": count}


def transform_upsert_core(**context):
    file_path = context["ti"].xcom_pull(task_ids="load_to_staging")
    fp = file_path["file"] if isinstance(file_path, dict) else find_latest_staging_file()
    with open(fp, "r", encoding="utf-8") as f:
        data = json.load(f)
    count = transform_and_upsert_core(data)
    return {"core_upserts": count}


def upsert_hist(**context):
    file_path = context["ti"].xcom_pull(task_ids="load_to_staging")
    fp = file_path["file"] if isinstance(file_path, dict) else find_latest_staging_file()
    with open(fp, "r", encoding="utf-8") as f:
        data = json.load(f)
    count = upsert_history(data)
    return {"history_inserts": count}


with DAG(
    dag_id="update_db",
    description="Load staging JSON to MongoDB and upsert into core and history",
    default_args=DEFAULT_ARGS,
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["youtube", "elt", "load"],
) as dag:

    load_task = PythonOperator(
        task_id="load_to_staging",
        python_callable=load_to_staging,
        provide_context=True,
    )

    core_task = PythonOperator(
        task_id="transform_and_upsert_core",
        python_callable=transform_upsert_core,
        provide_context=True,
    )

    history_task = PythonOperator(
        task_id="upsert_history",
        python_callable=upsert_hist,
        provide_context=True,
    )

    load_task >> [core_task, history_task]
