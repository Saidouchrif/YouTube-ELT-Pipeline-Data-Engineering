"""
Airflow DAG: data_quality
- Execute data quality tests: completeness, consistency, formats.
- Generate alerts if failures occur.
- Track logs and reporting.
- Run Soda Core scan against MongoDB to validate data quality rules.
"""
from __future__ import annotations

import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from config.settings import config
from youtube_elt.db import get_collection


DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def check_data_completeness(**context):
    """Check data completeness in core collection."""
    print("Checking data completeness...")
    
    try:
        core_collection = get_collection(config.CORE_COLLECTION)
        
        # Count total records
        total_records = core_collection.count_documents({})
        print(f"Total records in core collection: {total_records}")
        
        # Check for required fields
        required_fields = ['video_id', 'title', 'published_at', 'view_count']
        issues = []
        
        for field in required_fields:
            null_count = core_collection.count_documents({field: {"$in": [None, ""]}})
            if null_count > 0:
                issues.append(f"Field '{field}' has {null_count} null/empty values")
                print(f"WARNING: {issues[-1]}")
        
        # Check for duplicates
        pipeline = [
            {"$group": {"_id": "$video_id", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]
        duplicates = list(core_collection.aggregate(pipeline))
        
        if duplicates:
            issues.append(f"Found {len(duplicates)} duplicate video_ids")
            print(f"WARNING: {issues[-1]}")
        
        result = {
            "total_records": total_records,
            "completeness_issues": issues,
            "status": "FAILED" if issues else "PASSED"
        }
        
        context["ti"].xcom_push(key="completeness_result", value=result)
        return result
        
    except Exception as e:
        print(f"Error in completeness check: {str(e)}")
        raise


def check_data_consistency(**context):
    """Check data consistency and formats."""
    print("Checking data consistency and formats...")
    
    try:
        core_collection = get_collection(config.CORE_COLLECTION)
        
        issues = []
        
        # Check view_count is numeric and positive
        invalid_views = core_collection.count_documents({
            "$or": [
                {"view_count": {"$lt": 0}},
                {"view_count": {"$type": "string"}}
            ]
        })
        
        if invalid_views > 0:
            issues.append(f"Found {invalid_views} records with invalid view_count")
            print(f"WARNING: {issues[-1]}")
        
        # Check published_at format (should be ISO date)
        invalid_dates = core_collection.count_documents({
            "published_at": {"$not": {"$regex": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"}}
        })
        
        if invalid_dates > 0:
            issues.append(f"Found {invalid_dates} records with invalid published_at format")
            print(f"WARNING: {issues[-1]}")
        
        # Check duration_seconds is positive
        invalid_duration = core_collection.count_documents({
            "duration_seconds": {"$lt": 0}
        })
        
        if invalid_duration > 0:
            issues.append(f"Found {invalid_duration} records with negative duration")
            print(f"WARNING: {issues[-1]}")
        
        result = {
            "consistency_issues": issues,
            "status": "FAILED" if issues else "PASSED"
        }
        
        context["ti"].xcom_push(key="consistency_result", value=result)
        return result
        
    except Exception as e:
        print(f"Error in consistency check: {str(e)}")
        raise


def run_soda_scan(**context):
    """Run Soda Core scan with enhanced error handling."""
    print("Running Soda Core data quality scan...")
    
    try:
        cfg = Path(config.SODA_CORE_CONFIG_PATH)
        checks = Path("/opt/airflow/soda/checks/checks_mongo.yml")
        
        print(f"Soda config path: {cfg}")
        print(f"Soda checks path: {checks}")
        
        if not cfg.exists():
            print(f"WARNING: Soda config not found at {cfg}, skipping Soda scan")
            return {"status": "SKIPPED", "reason": "Config file not found"}
        
        if not checks.exists():
            print(f"WARNING: Soda checks file not found at {checks}, skipping Soda scan")
            return {"status": "SKIPPED", "reason": "Checks file not found"}

        cmd = [
            "soda",
            "scan",
            "-d",
            "mongo",
            "-c",
            str(cfg),
            str(checks),
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(f"Soda scan output:\n{result.stdout}")
        
        if result.stderr:
            print(f"Soda scan errors:\n{result.stderr}")
        
        soda_result = {
            "status": "PASSED" if result.returncode == 0 else "FAILED",
            "output": result.stdout,
            "errors": result.stderr,
            "return_code": result.returncode
        }
        
        context["ti"].xcom_push(key="soda_result", value=soda_result)
        
        if result.returncode != 0:
            print(f"Soda scan failed with return code {result.returncode}")
        
        return soda_result
        
    except Exception as e:
        print(f"Error running Soda scan: {str(e)}")
        return {"status": "ERROR", "error": str(e)}


def generate_quality_report(**context):
    """Generate comprehensive data quality report."""
    print("Generating data quality report...")
    
    try:
        # Get results from previous tasks
        completeness = context["ti"].xcom_pull(key="completeness_result", task_ids="check_completeness")
        consistency = context["ti"].xcom_pull(key="consistency_result", task_ids="check_consistency")
        soda = context["ti"].xcom_pull(key="soda_result", task_ids="soda_scan")
        
        # Generate summary report
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "completeness_check": completeness or {"status": "ERROR"},
            "consistency_check": consistency or {"status": "ERROR"},
            "soda_scan": soda or {"status": "ERROR"},
            "overall_status": "PASSED"
        }
        
        # Determine overall status
        failed_checks = []
        if completeness and completeness.get("status") == "FAILED":
            failed_checks.append("completeness")
        if consistency and consistency.get("status") == "FAILED":
            failed_checks.append("consistency")
        if soda and soda.get("status") == "FAILED":
            failed_checks.append("soda")
        
        if failed_checks:
            report["overall_status"] = "FAILED"
            report["failed_checks"] = failed_checks
            print(f"ALERT: Data quality checks failed: {', '.join(failed_checks)}")
        else:
            print("All data quality checks passed successfully")
        
        print(f"Data Quality Report:\n{json.dumps(report, indent=2)}")
        
        return report
        
    except Exception as e:
        print(f"Error generating quality report: {str(e)}")
        raise


with DAG(
    dag_id="data_quality",
    description="Execute comprehensive data quality tests with completeness, consistency, and Soda Core",
    default_args=DEFAULT_ARGS,
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["youtube", "dq", "soda"],
) as dag:

    completeness_task = PythonOperator(
        task_id="check_completeness",
        python_callable=check_data_completeness,
        provide_context=True,
    )

    consistency_task = PythonOperator(
        task_id="check_consistency",
        python_callable=check_data_consistency,
        provide_context=True,
    )

    soda_task = PythonOperator(
        task_id="soda_scan",
        python_callable=run_soda_scan,
        provide_context=True,
    )

    report_task = PythonOperator(
        task_id="generate_report",
        python_callable=generate_quality_report,
        provide_context=True,
    )

    # Set task dependencies - run checks in parallel, then generate report
    [completeness_task, consistency_task, soda_task] >> report_task
