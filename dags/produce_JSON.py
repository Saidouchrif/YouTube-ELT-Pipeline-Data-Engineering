"""
Airflow DAG: produce_JSON
- Extract YouTube data for channel handle and save timestamped JSON files to staging path.
- Handles retries and respects quota via extractor logic.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from config.settings import config
from plugins.youtube_elt.extract import extract_youtube_data


DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="produce_JSON",
    description="Extract YouTube channel data to JSON staging files",
    default_args=DEFAULT_ARGS,
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["youtube", "elt", "extract"],
) as dag:

    def _extract_and_save(**context):
        channel = config.YOUTUBE_CHANNEL_HANDLE
        max_videos = config.YOUTUBE_MAX_RESULTS
        output_dir = config.DATA_STAGING_PATH
        file_path = extract_youtube_data(channel_handle=channel, max_videos=max_videos, output_path=output_dir)
        # push path to XCom
        context["ti"].xcom_push(key="staging_file_path", value=file_path)
        return file_path

    extract_task = PythonOperator(
        task_id="extract_youtube_data",
        python_callable=_extract_and_save,
        provide_context=True,
    )

    extract_task
