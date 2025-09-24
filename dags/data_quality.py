"""
Airflow DAG: data_quality
- Run Soda Core scan against MongoDB to validate data quality rules.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from config.settings import config


DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def run_soda_scan():
    cfg = Path(config.SODA_CORE_CONFIG_PATH)
    checks = Path("/usr/local/airflow/soda/checks/checks_mongo.yml")
    if not cfg.exists():
        raise FileNotFoundError(f"Soda config not found: {cfg}")
    if not checks.exists():
        raise FileNotFoundError(f"Soda checks file not found: {checks}")

    cmd = [
        "soda",
        "scan",
        "-d",
        "mongo",
        "-c",
        str(cfg),
        str(checks),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Soda scan failed: {result.stdout}\n{result.stderr}")
    return result.stdout


with DAG(
    dag_id="data_quality",
    description="Run Soda Core data quality checks against MongoDB",
    default_args=DEFAULT_ARGS,
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["youtube", "dq", "soda"],
) as dag:

    dq_task = PythonOperator(
        task_id="soda_scan_mongo",
        python_callable=run_soda_scan,
    )

    dq_task
