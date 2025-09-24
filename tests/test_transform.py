import datetime
from plugins.youtube_elt.transform import (
    iso8601_duration_to_seconds,
    parse_published_at,
    classify_content,
    standardize_video,
    transform_dataset,
)


def test_iso8601_duration_to_seconds_regular():
    assert iso8601_duration_to_seconds("PT1H2M10S") == 3730


def test_iso8601_duration_to_seconds_short():
    assert iso8601_duration_to_seconds("PT45S") == 45


def test_iso8601_duration_to_seconds_invalid():
    assert iso8601_duration_to_seconds("INVALID") == 0


def test_parse_published_at_to_utc_z():
    ts = "2024-01-01T12:00:00+02:00"
    out = parse_published_at(ts)
    assert out.endswith("Z")


def test_classify_content_short_by_title():
    v = {"title": "Something #short", "duration_seconds": 80}
    assert classify_content(v) == "short"


def test_classify_content_short_by_duration():
    v = {"title": "Video", "duration_seconds": 59}
    assert classify_content(v) == "short"


def test_classify_content_longform():
    v = {"title": "Long Video", "duration_seconds": 1800}
    assert classify_content(v) == "longform"


def test_classify_content_live():
    v = {"title": "LIVE now!", "duration_seconds": 120}
    assert classify_content(v) == "live_or_premiere"


def test_standardize_video_fields(sample_dataset):
    video = sample_dataset["videos"][0]
    std = standardize_video(video)
    assert std["video_id"] == video["video_id"]
    assert "duration_seconds" in std
    assert "content_type" in std


def test_transform_dataset(sample_dataset):
    out = transform_dataset(sample_dataset)
    assert out["total_videos"] == 2
    assert len(out["videos"]) == 2
