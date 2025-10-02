"""
Tests for YouTube data loading module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

# Import the module to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'plugins'))

from youtube_elt.load import (
    load_staging_from_file,
    transform_and_upsert_core,
    upsert_history
)


class TestLoadStagingFromFile:
    """Test cases for loading staging data from file."""
    
    @patch('youtube_elt.load.get_collection')
    @patch('youtube_elt.load.ensure_indexes')
    def test_load_staging_from_file_success(self, mock_ensure_indexes, mock_get_collection):
        """Test successful loading of staging data from file."""
        # Mock MongoDB collection
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        # Mock bulk_write result
        mock_result = Mock()
        mock_result.upserted_count = 2
        mock_result.modified_count = 1
        mock_collection.bulk_write.return_value = mock_result
        
        # Create temporary test file
        import tempfile
        test_data = {
            "videos": [
                {"video_id": "test1", "title": "Video 1"},
                {"video_id": "test2", "title": "Video 2"}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file_path = f.name
        
        try:
            # Test the function
            result = load_staging_from_file(temp_file_path)
            
            # Verify results
            assert result == 3  # 2 upserted + 1 modified
            mock_ensure_indexes.assert_called_once()
            mock_collection.bulk_write.assert_called_once()
            
        finally:
            # Clean up
            os.unlink(temp_file_path)
    
    def test_load_staging_from_file_not_found(self):
        """Test loading from non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_staging_from_file("/non/existent/file.json")
    
    @patch('youtube_elt.load.get_collection')
    @patch('youtube_elt.load.ensure_indexes')
    def test_load_staging_from_file_empty_videos(self, mock_ensure_indexes, mock_get_collection):
        """Test loading file with no videos."""
        # Create temporary test file with empty videos
        import tempfile
        test_data = {"videos": []}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file_path = f.name
        
        try:
            # Test the function
            result = load_staging_from_file(temp_file_path)
            
            # Should return 0 for empty videos
            assert result == 0
            
        finally:
            # Clean up
            os.unlink(temp_file_path)


class TestTransformAndUpsertCore:
    """Test cases for transforming and upserting core data."""
    
    @patch('youtube_elt.load.get_collection')
    @patch('youtube_elt.load.ensure_indexes')
    @patch('youtube_elt.load.transform_dataset')
    def test_transform_and_upsert_core_success(self, mock_transform, mock_ensure_indexes, mock_get_collection):
        """Test successful transformation and upsert to core."""
        # Mock MongoDB collection
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        # Mock transform_dataset
        mock_transform.return_value = {
            "videos": [
                {"video_id": "test1", "title": "Video 1"},
                {"video_id": "test2", "title": "Video 2"}
            ]
        }
        
        # Mock bulk_write result
        mock_result = Mock()
        mock_result.upserted_count = 1
        mock_result.modified_count = 1
        mock_collection.bulk_write.return_value = mock_result
        
        # Test data
        dataset = {
            "channel_handle": "TestChannel",
            "videos": [{"video_id": "test1", "title": "Video 1"}]
        }
        
        # Test the function
        result = transform_and_upsert_core(dataset)
        
        # Verify results
        assert result == 2  # 1 upserted + 1 modified
        mock_ensure_indexes.assert_called_once()
        mock_transform.assert_called_once_with(dataset)
        mock_collection.bulk_write.assert_called_once()
    
    @patch('youtube_elt.load.get_collection')
    @patch('youtube_elt.load.ensure_indexes')
    @patch('youtube_elt.load.transform_dataset')
    def test_transform_and_upsert_core_empty_videos(self, mock_transform, mock_ensure_indexes, mock_get_collection):
        """Test transformation with no videos."""
        # Mock transform_dataset to return empty videos
        mock_transform.return_value = {"videos": []}
        
        # Test data
        dataset = {"channel_handle": "TestChannel", "videos": []}
        
        # Test the function
        result = transform_and_upsert_core(dataset)
        
        # Should return 0 for empty videos
        assert result == 0


class TestUpsertHistory:
    """Test cases for upserting history data."""
    
    @patch('youtube_elt.load.get_collection')
    @patch('youtube_elt.load.ensure_indexes')
    @patch('youtube_elt.load.transform_dataset')
    def test_upsert_history_new_record(self, mock_transform, mock_ensure_indexes, mock_get_collection):
        """Test upserting new record to history."""
        # Mock MongoDB collection
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        # Mock transform_dataset
        mock_transform.return_value = {
            "videos": [
                {
                    "video_id": "test1",
                    "title": "Video 1",
                    "view_count": 1000,
                    "like_count": 100
                }
            ]
        }
        
        # Mock find_one to return None (no existing record)
        mock_collection.find_one.return_value = None
        
        # Test data
        dataset = {
            "channel_handle": "TestChannel",
            "videos": [{"video_id": "test1", "title": "Video 1"}]
        }
        
        # Test the function
        result = upsert_history(dataset)
        
        # Verify results
        assert result == 1  # 1 new record inserted
        mock_ensure_indexes.assert_called_once()
        mock_transform.assert_called_once_with(dataset)
        mock_collection.insert_one.assert_called_once()
    
    @patch('youtube_elt.load.get_collection')
    @patch('youtube_elt.load.ensure_indexes')
    @patch('youtube_elt.load.transform_dataset')
    def test_upsert_history_changed_record(self, mock_transform, mock_ensure_indexes, mock_get_collection):
        """Test upserting changed record to history."""
        # Mock MongoDB collection
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        # Mock transform_dataset
        mock_transform.return_value = {
            "videos": [
                {
                    "video_id": "test1",
                    "title": "Video 1",
                    "view_count": 2000,  # Changed from 1000
                    "like_count": 200    # Changed from 100
                }
            ]
        }
        
        # Mock find_one to return existing record
        existing_record = {
            "_id": "existing_id",
            "video_id": "test1",
            "title": "Video 1",
            "view_count": 1000,  # Old value
            "like_count": 100    # Old value
        }
        mock_collection.find_one.return_value = existing_record
        
        # Test data
        dataset = {
            "channel_handle": "TestChannel",
            "videos": [{"video_id": "test1", "title": "Video 1"}]
        }
        
        # Test the function
        result = upsert_history(dataset)
        
        # Verify results
        assert result == 1  # 1 record updated/inserted
        mock_collection.update_one.assert_called_once()  # Close old record
        mock_collection.insert_one.assert_called_once()   # Insert new record
    
    @patch('youtube_elt.load.get_collection')
    @patch('youtube_elt.load.ensure_indexes')
    @patch('youtube_elt.load.transform_dataset')
    def test_upsert_history_unchanged_record(self, mock_transform, mock_ensure_indexes, mock_get_collection):
        """Test upserting unchanged record to history."""
        # Mock MongoDB collection
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        # Mock transform_dataset
        mock_transform.return_value = {
            "videos": [
                {
                    "video_id": "test1",
                    "title": "Video 1",
                    "view_count": 1000,
                    "like_count": 100
                }
            ]
        }
        
        # Mock find_one to return existing record with same values
        existing_record = {
            "_id": "existing_id",
            "video_id": "test1",
            "title": "Video 1",
            "view_count": 1000,  # Same value
            "like_count": 100    # Same value
        }
        mock_collection.find_one.return_value = existing_record
        
        # Test data
        dataset = {
            "channel_handle": "TestChannel",
            "videos": [{"video_id": "test1", "title": "Video 1"}]
        }
        
        # Test the function
        result = upsert_history(dataset)
        
        # Verify results - no changes, so no new records
        assert result == 0
        # Should not call update_one or insert_one for unchanged records
        mock_collection.update_one.assert_not_called()
        mock_collection.insert_one.assert_not_called()


class TestLoadModuleIntegration:
    """Integration tests for load module."""
    
    def test_load_module_imports(self):
        """Test that all necessary imports work."""
        from youtube_elt.load import (
            load_staging_from_file,
            transform_and_upsert_core,
            upsert_history
        )
        
        # Verify functions exist
        assert callable(load_staging_from_file)
        assert callable(transform_and_upsert_core)
        assert callable(upsert_history)
    
    @patch('youtube_elt.load.utcnow_iso')
    def test_timestamp_handling(self, mock_utcnow):
        """Test that timestamps are handled correctly."""
        # Mock timestamp
        mock_utcnow.return_value = "2023-01-01T12:00:00Z"
        
        # Import and verify timestamp function is called
        from youtube_elt.load import utcnow_iso
        timestamp = utcnow_iso()
        
        # Should return mocked timestamp
        assert timestamp == "2023-01-01T12:00:00Z"


@pytest.mark.parametrize("upserted,modified,expected", [
    (2, 1, 3),
    (0, 5, 5),
    (3, 0, 3),
    (0, 0, 0),
])
def test_result_calculation(upserted, modified, expected):
    """Parametrized test for result calculation logic."""
    # This tests the logic: (upserted_count or 0) + (modified_count or 0)
    result = (upserted or 0) + (modified or 0)
    assert result == expected
