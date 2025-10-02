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
from youtube_elt.extract import extract_youtube_data
from youtube_elt.load import load_staging_from_file


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
        """Extract YouTube data and save to JSON file."""
        channel = config.YOUTUBE_CHANNEL_HANDLE
        max_videos = config.YOUTUBE_MAX_RESULTS
        output_dir = config.DATA_STAGING_PATH
        
        print(f"Extracting data for channel: {channel}")
        print(f"Max videos: {max_videos}")
        print(f"Output directory: {output_dir}")
        
        file_path = extract_youtube_data(channel_handle=channel, max_videos=max_videos, output_path=output_dir)
        
        print(f"Data extracted successfully to: {file_path}")
        # push path to XCom
        context["ti"].xcom_push(key="staging_file_path", value=file_path)
        return file_path

    def _load_to_mongodb(**context):
        """Load JSON file to MongoDB staging collection."""
        # Get file path from previous task
        file_path = context["ti"].xcom_pull(key="staging_file_path", task_ids="extract_youtube_data")
        
        if not file_path:
            raise ValueError("No staging file path found in XCom")
        
        print(f"Loading file to MongoDB: {file_path}")
        
        # Load to staging collection with upsert
        records_loaded = load_staging_from_file(file_path)
        
        print(f"Successfully loaded {records_loaded} records to MongoDB staging collection")
        return records_loaded

    extract_task = PythonOperator(
        task_id="extract_youtube_data",
        python_callable=_extract_and_save,
        provide_context=True,
    )

    load_task = PythonOperator(
        task_id="load_to_mongodb",
        python_callable=_load_to_mongodb,
        provide_context=True,
    )

    # Set task dependencies
    extract_task >> load_task
