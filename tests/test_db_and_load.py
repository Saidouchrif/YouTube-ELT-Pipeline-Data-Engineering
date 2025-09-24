import json
from pathlib import Path

from plugins.youtube_elt.db import get_collection, ensure_indexes
from plugins.youtube_elt.load import (
    load_staging_from_file,
    transform_and_upsert_core,
    upsert_history,
)


def test_ensure_indexes_no_error():
    # Should create indexes without raising
    ensure_indexes()
    staging = get_collection("staging_data")
    idx_names = [i["name"] for i in staging.list_indexes()]
    assert "ux_staging_video" in idx_names


def test_load_staging_from_file(tmp_path, sample_dataset):
    file_path = tmp_path / "stage.json"
    file_path.write_text(json.dumps(sample_dataset), encoding="utf-8")

    inserted = load_staging_from_file(str(file_path))
    assert inserted >= 1

    staging = get_collection("staging_data")
    assert staging.count_documents({}) == 2


def test_transform_and_upsert_core(sample_dataset):
    count = transform_and_upsert_core(sample_dataset)
    assert count == 2

    core = get_collection("core_data")
    assert core.count_documents({}) == 2


def test_upsert_history_inserts(sample_dataset):
    # First run should insert 2 history records
    count1 = upsert_history(sample_dataset)
    assert count1 == 2

    # Second run with same data should insert 0 (no changes)
    count2 = upsert_history(sample_dataset)
    assert count2 == 0

    # Modify title to force change and new version
    sample_dataset_mut = json.loads(json.dumps(sample_dataset))
    sample_dataset_mut["videos"][0]["title"] = "Changed title"
    count3 = upsert_history(sample_dataset_mut)
    assert count3 == 1

    history = get_collection("history_data")
    assert history.count_documents({"video_id": sample_dataset["videos"][0]["video_id"]}) >= 2
