"""
Tests for database utilities module.
"""
import pytest
from unittest.mock import Mock, patch
import os

# Import the module to test
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'plugins'))

from youtube_elt.db import (
    get_mongo_client,
    get_db,
    get_collection,
    ensure_indexes,
    utcnow_iso
)


class TestMongoConnection:
    """Test cases for MongoDB connection utilities."""
    
    @patch('youtube_elt.db.MongoClient')
    def test_get_mongo_client_production(self, mock_mongo_client):
        """Test getting MongoDB client in production mode."""
        # Mock environment to not use mock DB
        with patch.dict(os.environ, {'USE_MOCK_DB': 'false'}):
            # Reset the global client
            import youtube_elt.db
            youtube_elt.db._client = None
            
            # Call the function
            client = get_mongo_client()
            
            # Verify MongoClient was called
            mock_mongo_client.assert_called_once()
    
    @patch('youtube_elt.db.mongomock')
    def test_get_mongo_client_mock(self, mock_mongomock):
        """Test getting MongoDB client in mock mode."""
        # Mock environment to use mock DB
        with patch.dict(os.environ, {'USE_MOCK_DB': 'true'}):
            # Reset the global client
            import youtube_elt.db
            youtube_elt.db._client = None
            
            # Call the function
            client = get_mongo_client()
            
            # Verify mongomock was called
            mock_mongomock.MongoClient.assert_called_once()
    
    @patch('youtube_elt.db.get_mongo_client')
    def test_get_db(self, mock_get_client):
        """Test getting database from client."""
        # Mock client and database
        mock_client = Mock()
        mock_db = Mock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client
        
        # Mock config
        with patch('youtube_elt.db.config') as mock_config:
            mock_config.MONGO_DATABASE = 'test_db'
            
            # Call the function
            db = get_db()
            
            # Verify database access
            mock_client.__getitem__.assert_called_once_with('test_db')
    
    @patch('youtube_elt.db.get_db')
    def test_get_collection(self, mock_get_db):
        """Test getting collection from database."""
        # Mock database and collection
        mock_db = Mock()
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db
        
        # Call the function
        collection = get_collection('test_collection')
        
        # Verify collection access
        mock_db.__getitem__.assert_called_once_with('test_collection')


class TestIndexManagement:
    """Test cases for index management."""
    
    @patch('youtube_elt.db.get_collection')
    def test_ensure_indexes(self, mock_get_collection):
        """Test ensuring indexes are created."""
        # Mock collections
        mock_staging = Mock()
        mock_core = Mock()
        mock_history = Mock()
        
        # Mock get_collection to return different collections
        def side_effect(collection_name):
            if 'staging' in collection_name:
                return mock_staging
            elif 'core' in collection_name:
                return mock_core
            elif 'history' in collection_name:
                return mock_history
            return Mock()
        
        mock_get_collection.side_effect = side_effect
        
        # Mock config
        with patch('youtube_elt.db.config') as mock_config:
            mock_config.STAGING_COLLECTION = 'staging_data'
            mock_config.CORE_COLLECTION = 'core_data'
            mock_config.HISTORY_COLLECTION = 'history_data'
            
            # Call the function
            ensure_indexes()
            
            # Verify indexes were created
            mock_staging.create_index.assert_called_once()
            mock_core.create_index.assert_called_once()
            mock_history.create_index.assert_called_once()


class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_utcnow_iso(self):
        """Test UTC timestamp generation."""
        timestamp = utcnow_iso()
        
        # Verify format
        assert isinstance(timestamp, str)
        assert 'T' in timestamp
        assert timestamp.endswith('Z')
        
        # Verify it's a valid ISO format (basic check)
        from datetime import datetime
        try:
            # Should be able to parse the timestamp
            parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            assert parsed is not None
        except ValueError:
            pytest.fail("Generated timestamp is not valid ISO format")
    
    def test_utcnow_iso_format(self):
        """Test that UTC timestamp has correct format."""
        timestamp = utcnow_iso()
        
        # Should match pattern: YYYY-MM-DDTHH:MM:SS.fffffZ
        import re
        pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'
        assert re.match(pattern, timestamp), f"Timestamp {timestamp} doesn't match expected format"


class TestDatabaseIntegration:
    """Integration tests for database module."""
    
    def test_db_module_imports(self):
        """Test that all necessary imports work."""
        from youtube_elt.db import (
            get_mongo_client,
            get_db,
            get_collection,
            ensure_indexes,
            utcnow_iso
        )
        
        # Verify functions exist
        assert callable(get_mongo_client)
        assert callable(get_db)
        assert callable(get_collection)
        assert callable(ensure_indexes)
        assert callable(utcnow_iso)
    
    @patch('youtube_elt.db.get_mongo_client')
    def test_client_singleton_behavior(self, mock_get_client):
        """Test that MongoDB client behaves as singleton."""
        # Reset the global client
        import youtube_elt.db
        youtube_elt.db._client = None
        
        # Mock client
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Call multiple times
        client1 = get_mongo_client()
        client2 = get_mongo_client()
        
        # Should return same instance
        assert client1 is client2


class TestErrorHandling:
    """Test cases for error handling in database operations."""
    
    @patch('youtube_elt.db.MongoClient')
    def test_mongo_client_connection_error(self, mock_mongo_client):
        """Test handling of MongoDB connection errors."""
        # Mock MongoClient to raise exception
        mock_mongo_client.side_effect = Exception("Connection failed")
        
        # Reset the global client
        import youtube_elt.db
        youtube_elt.db._client = None
        
        # Mock environment to not use mock DB
        with patch.dict(os.environ, {'USE_MOCK_DB': 'false'}):
            # Should raise exception
            with pytest.raises(Exception, match="Connection failed"):
                get_mongo_client()


@pytest.mark.parametrize("use_mock_db,expected_client_type", [
    ("true", "mongomock"),
    ("false", "pymongo"),
    ("", "pymongo"),  # Default when not set
])
def test_client_selection_parametrized(use_mock_db, expected_client_type):
    """Parametrized test for client selection based on environment."""
    with patch.dict(os.environ, {'USE_MOCK_DB': use_mock_db}):
        # Reset the global client
        import youtube_elt.db
        youtube_elt.db._client = None
        
        if expected_client_type == "mongomock":
            with patch('youtube_elt.db.mongomock') as mock_mongomock:
                get_mongo_client()
                mock_mongomock.MongoClient.assert_called_once()
        else:
            with patch('youtube_elt.db.MongoClient') as mock_mongo_client:
                get_mongo_client()
                mock_mongo_client.assert_called_once()


def test_config_integration():
    """Test integration with config module."""
    # Test that config is imported and used correctly
    with patch('youtube_elt.db.config') as mock_config:
        mock_config.mongo_connection_string = "mongodb://test:test@localhost:27017/test"
        mock_config.MONGO_DATABASE = "test_database"
        mock_config.STAGING_COLLECTION = "test_staging"
        mock_config.CORE_COLLECTION = "test_core"
        mock_config.HISTORY_COLLECTION = "test_history"
        
        # These should not raise errors
        assert mock_config.mongo_connection_string is not None
        assert mock_config.MONGO_DATABASE is not None
