"""
Tests for YouTube data extraction module.
"""
import pytest
from unittest.mock import Mock, patch
import json
from datetime import datetime

# Import the module to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'plugins'))

from youtube_elt.extract import YouTubeExtractor, YouTubeAPIError


class TestYouTubeExtractor:
    """Test cases for YouTubeExtractor class."""
    
    def test_extractor_initialization(self):
        """Test that extractor initializes correctly."""
        extractor = YouTubeExtractor(api_key="test_key", channel_handle="TestChannel")
        assert extractor.api_key == "test_key"
        assert extractor.channel_handle == "TestChannel"
        assert extractor.quota_used == 0
    
    def test_extractor_initialization_without_api_key(self):
        """Test that extractor raises error without API key."""
        with pytest.raises(YouTubeAPIError):
            YouTubeExtractor(api_key="", channel_handle="TestChannel")
    
    def test_quota_cost_estimation(self):
        """Test quota cost estimation for different endpoints."""
        extractor = YouTubeExtractor(api_key="test_key", channel_handle="TestChannel")
        
        # Test different URL patterns
        assert extractor._estimate_quota_cost("https://www.googleapis.com/youtube/v3/channels") == 1
        assert extractor._estimate_quota_cost("https://www.googleapis.com/youtube/v3/videos") == 1
        assert extractor._estimate_quota_cost("https://www.googleapis.com/youtube/v3/playlistItems") == 1
    
    @patch('youtube_elt.extract.requests.get')
    def test_api_request_success(self, mock_get):
        """Test successful API request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [{"id": "test_id"}]}
        mock_get.return_value = mock_response
        
        extractor = YouTubeExtractor(api_key="test_key", channel_handle="TestChannel")
        result = extractor._make_api_request("https://test.com", {"param": "value"})
        
        assert result == {"items": [{"id": "test_id"}]}
        assert extractor.quota_used > 0
    
    @patch('youtube_elt.extract.requests.get')
    def test_api_request_quota_exceeded(self, mock_get):
        """Test API request when quota is exceeded."""
        # Mock quota exceeded response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "error": {
                "code": 403,
                "message": "Quota exceeded"
            }
        }
        mock_get.return_value = mock_response
        
        extractor = YouTubeExtractor(api_key="test_key", channel_handle="TestChannel")
        
        with pytest.raises(YouTubeAPIError):
            extractor._make_api_request("https://test.com", {"param": "value"})
    
    def test_save_to_json(self):
        """Test saving data to JSON file."""
        extractor = YouTubeExtractor(api_key="test_key", channel_handle="TestChannel")
        
        test_data = {
            "channel_handle": "TestChannel",
            "extraction_date": datetime.utcnow().isoformat(),
            "total_videos": 1,
            "videos": [{"video_id": "test123", "title": "Test Video"}]
        }
        
        # Test with temporary directory
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = extractor.save_to_json(test_data, output_path=temp_dir)
            
            # Verify file was created
            assert os.path.exists(file_path)
            
            # Verify content
            with open(file_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            
            assert saved_data["channel_handle"] == "TestChannel"
            assert saved_data["total_videos"] == 1
            assert len(saved_data["videos"]) == 1


class TestYouTubeAPIError:
    """Test cases for YouTubeAPIError exception."""
    
    def test_youtube_api_error_creation(self):
        """Test that YouTubeAPIError can be created and raised."""
        error_message = "Test error message"
        
        with pytest.raises(YouTubeAPIError) as exc_info:
            raise YouTubeAPIError(error_message)
        
        assert str(exc_info.value) == error_message


def test_extract_module_imports():
    """Test that all necessary imports work."""
    from youtube_elt.extract import YouTubeExtractor, YouTubeAPIError, QuotaExceededError
    
    # Verify classes exist
    assert YouTubeExtractor is not None
    assert YouTubeAPIError is not None
    assert QuotaExceededError is not None


@pytest.mark.parametrize("api_key,channel_handle,should_raise", [
    ("valid_key", "ValidChannel", False),
    ("", "ValidChannel", True),
    (None, "ValidChannel", True),
    ("valid_key", "", False),  # Empty channel should not raise during init
])
def test_extractor_initialization_parametrized(api_key, channel_handle, should_raise):
    """Parametrized test for extractor initialization."""
    if should_raise:
        with pytest.raises(YouTubeAPIError):
            YouTubeExtractor(api_key=api_key, channel_handle=channel_handle)
    else:
        extractor = YouTubeExtractor(api_key=api_key, channel_handle=channel_handle)
        assert extractor.api_key == api_key
        assert extractor.channel_handle == channel_handle
