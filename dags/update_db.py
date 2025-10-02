"""
Airflow DAG: update_db
- Read data from MongoDB staging collection.
- Apply transformations and data cleaning (types, formats, duplicates).
- Load into core schema with UPSERT operations.
- Maintain history SCD2 style.
- Log success/errors in Airflow.
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
from youtube_elt.load import load_staging_from_file, transform_and_upsert_core, upsert_history
from youtube_elt.db import get_collection


DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retry_delay": timedelta(minutes=5),
}


def find_latest_staging_file() -> str:
    pattern = os.path.join(config.DATA_STAGING_PATH, f"youtube_data_{config.YOUTUBE_CHANNEL_HANDLE}_*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No staging files found in {config.DATA_STAGING_PATH}")
    return files[-1]


def read_staging_data(**context):
    """Read data from MongoDB staging collection."""
    print("Reading data from MongoDB staging collection...")
    
    try:
        staging_collection = get_collection(config.STAGING_COLLECTION)
        
        # Get all records from staging (exclude MongoDB _id field)
        staging_records = list(staging_collection.find({}, {"_id": 0}))
        
        if not staging_records:
            print("No records found in staging collection")
            return {"records_count": 0}
        
        print(f"Found {len(staging_records)} records in staging collection")
        
        # Convert to the format expected by transform functions
        dataset = {
            "channel_handle": config.YOUTUBE_CHANNEL_HANDLE,
            "extraction_date": datetime.utcnow().isoformat(),
            "total_videos": len(staging_records),
            "videos": staging_records
        }
        
        # Store dataset in XCom for next tasks
        context["ti"].xcom_push(key="staging_dataset", value=dataset)
        
        return {"records_count": len(staging_records)}
        
    except Exception as e:
        print(f"Error reading staging data: {str(e)}")
        raise


def transform_upsert_core(**context):
    """Transform staging data and upsert to core collection."""
    print("Transforming and upserting data to core collection...")
    
    try:
        # Get dataset from previous task
        dataset = context["ti"].xcom_pull(key="staging_dataset", task_ids="read_staging_data")
        
        if not dataset:
            raise ValueError("No staging dataset found in XCom")
        
        print(f"Processing {dataset['total_videos']} videos for core collection")
        
        # Transform and upsert to core
        count = transform_and_upsert_core(dataset)
        
        print(f"Successfully upserted {count} records to core collection")
        return {"core_upserts": count}
        
    except Exception as e:
        print(f"Error in transform_upsert_core: {str(e)}")
        raise


def upsert_hist(**context):
    """Upsert data to history collection with SCD2 logic."""
    print("Upserting data to history collection...")
    
    try:
        # Get dataset from previous task
        dataset = context["ti"].xcom_pull(key="staging_dataset", task_ids="read_staging_data")
        
        if not dataset:
            raise ValueError("No staging dataset found in XCom")
        
        print(f"Processing {dataset['total_videos']} videos for history collection")
        
        # Upsert to history with SCD2
        count = upsert_history(dataset)
        
        print(f"Successfully processed {count} records in history collection")
        return {"history_inserts": count}
        
    except Exception as e:
        print(f"Error in upsert_hist: {str(e)}")
        raise


with DAG(
    dag_id="update_db",
    description="Load staging JSON to MongoDB and upsert into core and history",
    default_args=DEFAULT_ARGS,
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["youtube", "elt", "load"],
) as dag:

    read_task = PythonOperator(
        task_id="read_staging_data",
        python_callable=read_staging_data,
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

    # Set task dependencies
    read_task >> [core_task, history_task]
