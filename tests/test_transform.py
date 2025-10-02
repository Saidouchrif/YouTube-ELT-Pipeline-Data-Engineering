"""
Tests for YouTube data transformation module.
"""
import pytest
from datetime import datetime

# Import the module to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'plugins'))

from youtube_elt.transform import (
    iso8601_duration_to_seconds,
    parse_published_at,
    classify_content,
    standardize_video,
    transform_dataset
)


class TestDurationConversion:
    """Test cases for ISO 8601 duration conversion."""
    
    def test_iso8601_duration_to_seconds_valid(self):
        """Test conversion of valid ISO 8601 durations."""
        # Test various duration formats
        assert iso8601_duration_to_seconds("PT1M30S") == 90  # 1 minute 30 seconds
        assert iso8601_duration_to_seconds("PT3M33S") == 213  # 3 minutes 33 seconds
        assert iso8601_duration_to_seconds("PT1H2M10S") == 3730  # 1 hour 2 minutes 10 seconds
        assert iso8601_duration_to_seconds("PT45S") == 45  # 45 seconds
        assert iso8601_duration_to_seconds("PT2M") == 120  # 2 minutes
        assert iso8601_duration_to_seconds("PT1H") == 3600  # 1 hour
    
    def test_iso8601_duration_to_seconds_invalid(self):
        """Test conversion of invalid durations returns 0."""
        assert iso8601_duration_to_seconds("invalid") == 0
        assert iso8601_duration_to_seconds("") == 0
        assert iso8601_duration_to_seconds("PT") == 0
        assert iso8601_duration_to_seconds("123") == 0


class TestDateParsing:
    """Test cases for date parsing."""
    
    def test_parse_published_at_valid(self):
        """Test parsing of valid published_at timestamps."""
        # Test with Z timezone
        result = parse_published_at("2023-01-01T12:00:00Z")
        assert result == "2023-01-01T12:00:00Z"
        
        # Test with +00:00 timezone
        result = parse_published_at("2023-01-01T12:00:00+00:00")
        assert result == "2023-01-01T12:00:00Z"
    
    def test_parse_published_at_invalid(self):
        """Test parsing of invalid timestamps returns original."""
        invalid_date = "invalid-date"
        result = parse_published_at(invalid_date)
        assert result == invalid_date
        
        # Test empty string
        result = parse_published_at("")
        assert result == ""


class TestContentClassification:
    """Test cases for content type classification."""
    
    def test_classify_content_short(self):
        """Test classification of short content."""
        video = {"title": "Quick #short video", "duration_seconds": 30}
        assert classify_content(video) == "short"
        
        video = {"title": "Regular video", "duration_seconds": 45}
        assert classify_content(video) == "short"
    
    def test_classify_content_longform(self):
        """Test classification of longform content."""
        video = {"title": "Long documentary", "duration_seconds": 1500}  # 25 minutes
        assert classify_content(video) == "longform"
    
    def test_classify_content_live(self):
        """Test classification of live content."""
        video = {"title": "Live stream event", "duration_seconds": 600}
        assert classify_content(video) == "live_or_premiere"
        
        video = {"title": "Movie premiere tonight", "duration_seconds": 600}
        assert classify_content(video) == "live_or_premiere"
    
    def test_classify_content_standard(self):
        """Test classification of standard content."""
        video = {"title": "Regular video", "duration_seconds": 300}  # 5 minutes
        assert classify_content(video) == "standard"


class TestVideoStandardization:
    """Test cases for video standardization."""
    
    def test_standardize_video_complete(self):
        """Test standardization of complete video data."""
        video_data = {
            "video_id": "test123",
            "title": "  Test Video  ",
            "description": "Test description",
            "published_at": "2023-01-01T12:00:00Z",
            "duration": "PT5M30S",
            "view_count": "1000000",
            "like_count": "50000",
            "comment_count": "1000",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "channel_id": "UC123",
            "channel_title": "Test Channel",
            "tags": ["test", "video"],
            "category_id": "22",
            "default_language": "en",
            "default_audio_language": "en"
        }
        
        result = standardize_video(video_data)
        
        # Check basic fields
        assert result["video_id"] == "test123"
        assert result["title"] == "Test Video"  # Should be trimmed
        assert result["duration_seconds"] == 330  # 5 minutes 30 seconds
        assert result["view_count"] == 1000000
        assert result["like_count"] == 50000
        assert result["comment_count"] == 1000
        assert result["content_type"] == "standard"
    
    def test_standardize_video_missing_fields(self):
        """Test standardization with missing fields."""
        video_data = {
            "video_id": "test123",
            "title": "Test Video"
        }
        
        result = standardize_video(video_data)
        
        # Check default values
        assert result["video_id"] == "test123"
        assert result["title"] == "Test Video"
        assert result["description"] == ""
        assert result["duration_seconds"] == 0
        assert result["view_count"] == 0
        assert result["like_count"] == 0
        assert result["comment_count"] == 0
        assert result["tags"] == []
        assert result["category_id"] == ""
    
    def test_standardize_video_null_values(self):
        """Test standardization with null values."""
        video_data = {
            "video_id": "test123",
            "title": "Test Video",
            "view_count": None,
            "like_count": None,
            "tags": None
        }
        
        result = standardize_video(video_data)
        
        # Check null handling
        assert result["view_count"] == 0
        assert result["like_count"] == 0
        assert result["tags"] == []


class TestDatasetTransformation:
    """Test cases for dataset transformation."""
    
    def test_transform_dataset_complete(self):
        """Test transformation of complete dataset."""
        dataset = {
            "channel_handle": "TestChannel",
            "extraction_date": "2023-01-01T12:00:00Z",
            "videos": [
                {
                    "video_id": "test1",
                    "title": "Video 1",
                    "duration": "PT3M30S",
                    "view_count": "1000",
                    "like_count": "100",
                    "comment_count": "10"
                },
                {
                    "video_id": "test2",
                    "title": "Video 2",
                    "duration": "PT1M",
                    "view_count": "500",
                    "like_count": "50",
                    "comment_count": "5"
                }
            ]
        }
        
        result = transform_dataset(dataset)
        
        # Check dataset structure
        assert result["channel_handle"] == "TestChannel"
        assert result["extraction_date"] == "2023-01-01T12:00:00Z"
        assert result["total_videos"] == 2
        assert len(result["videos"]) == 2
        
        # Check first video transformation
        video1 = result["videos"][0]
        assert video1["video_id"] == "test1"
        assert video1["duration_seconds"] == 210  # 3 minutes 30 seconds
        assert video1["view_count"] == 1000
    
    def test_transform_dataset_empty_videos(self):
        """Test transformation of dataset with no videos."""
        dataset = {
            "channel_handle": "TestChannel",
            "extraction_date": "2023-01-01T12:00:00Z",
            "videos": []
        }
        
        result = transform_dataset(dataset)
        
        assert result["channel_handle"] == "TestChannel"
        assert result["total_videos"] == 0
        assert result["videos"] == []
    
    def test_transform_dataset_missing_videos_key(self):
        """Test transformation of dataset without videos key."""
        dataset = {
            "channel_handle": "TestChannel",
            "extraction_date": "2023-01-01T12:00:00Z"
        }
        
        result = transform_dataset(dataset)
        
        assert result["channel_handle"] == "TestChannel"
        assert result["total_videos"] == 0
        assert result["videos"] == []


@pytest.mark.parametrize("duration,expected_seconds", [
    ("PT1M30S", 90),
    ("PT3M33S", 213),
    ("PT1H2M10S", 3730),
    ("PT45S", 45),
    ("PT2M", 120),
    ("PT1H", 3600),
    ("invalid", 0),
    ("", 0),
])
def test_duration_conversion_parametrized(duration, expected_seconds):
    """Parametrized test for duration conversion."""
    assert iso8601_duration_to_seconds(duration) == expected_seconds


@pytest.mark.parametrize("title,duration,expected_type", [
    ("Quick #short video", 30, "short"),
    ("Live stream event", 600, "live_or_premiere"),
    ("Movie premiere tonight", 600, "live_or_premiere"),
    ("Long documentary", 1500, "longform"),
    ("Regular video", 300, "standard"),
])
def test_content_classification_parametrized(title, duration, expected_type):
    """Parametrized test for content classification."""
    video = {"title": title, "duration_seconds": duration}
    assert classify_content(video) == expected_type
