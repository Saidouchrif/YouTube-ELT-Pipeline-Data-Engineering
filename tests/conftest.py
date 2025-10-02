"""
Pytest configuration and fixtures for YouTube ELT Pipeline tests.
"""
import pytest
import os
import sys
from unittest.mock import patch

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'plugins'))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    test_env = {
        'USE_MOCK_DB': 'true',
        'YOUTUBE_API_KEY': 'test_api_key',
        'YOUTUBE_CHANNEL_HANDLE': 'TestChannel',
        'YOUTUBE_MAX_RESULTS': '10',
        'YOUTUBE_QUOTA_LIMIT': '1000',
        'MONGO_HOST': 'localhost',
        'MONGO_PORT': '27017',
        'MONGO_USERNAME': 'test_user',
        'MONGO_PASSWORD': 'test_password',
        'MONGO_DATABASE': 'test_database',
        'DATA_STAGING_PATH': '/tmp/test_staging/',
        'DATA_PROCESSED_PATH': '/tmp/test_processed/',
        'LOG_LEVEL': 'DEBUG',
        'RETRY_ATTEMPTS': '2',
        'RETRY_DELAY': '1'
    }
    
    with patch.dict(os.environ, test_env):
        yield


@pytest.fixture
def sample_video_data():
    """Provide sample video data for testing."""
    return {
        "video_id": "test123",
        "title": "Test Video Title",
        "description": "Test video description",
        "published_at": "2023-01-01T12:00:00Z",
        "duration": "PT5M30S",
        "view_count": 1000000,
        "like_count": 50000,
        "comment_count": 1000,
        "thumbnail_url": "https://example.com/thumbnail.jpg",
        "channel_id": "UC123456789",
        "channel_title": "Test Channel",
        "tags": ["test", "video", "sample"],
        "category_id": "22",
        "default_language": "en",
        "default_audio_language": "en"
    }


@pytest.fixture
def sample_dataset():
    """Provide sample dataset for testing."""
    return {
        "channel_handle": "TestChannel",
        "extraction_date": "2023-01-01T12:00:00Z",
        "total_videos": 2,
        "videos": [
            {
                "video_id": "test1",
                "title": "Video 1",
                "duration": "PT3M30S",
                "view_count": 1000,
                "like_count": 100,
                "comment_count": 10
            },
            {
                "video_id": "test2",
                "title": "Video 2",
                "duration": "PT1M",
                "view_count": 500,
                "like_count": 50,
                "comment_count": 5
            }
        ]
    }


@pytest.fixture
def mock_mongo_collection():
    """Provide a mock MongoDB collection."""
    from unittest.mock import Mock
    
    collection = Mock()
    collection.find.return_value = []
    collection.find_one.return_value = None
    collection.count_documents.return_value = 0
    collection.insert_one.return_value = Mock(inserted_id="test_id")
    collection.insert_many.return_value = Mock(inserted_ids=["id1", "id2"])
    collection.update_one.return_value = Mock(modified_count=1)
    collection.bulk_write.return_value = Mock(upserted_count=1, modified_count=1)
    collection.create_index.return_value = "test_index"
    
    return collection


@pytest.fixture
def mock_config():
    """Provide a mock configuration object."""
    from unittest.mock import Mock
    
    config = Mock()
    config.YOUTUBE_API_KEY = 'test_api_key'
    config.YOUTUBE_CHANNEL_HANDLE = 'TestChannel'
    config.YOUTUBE_MAX_RESULTS = 10
    config.YOUTUBE_QUOTA_LIMIT = 1000
    config.MONGO_HOST = 'localhost'
    config.MONGO_PORT = 27017
    config.MONGO_USERNAME = 'test_user'
    config.MONGO_PASSWORD = 'test_password'
    config.MONGO_DATABASE = 'test_database'
    config.STAGING_COLLECTION = 'staging_data'
    config.CORE_COLLECTION = 'core_data'
    config.HISTORY_COLLECTION = 'history_data'
    config.DATA_STAGING_PATH = '/tmp/test_staging/'
    config.DATA_PROCESSED_PATH = '/tmp/test_processed/'
    config.mongo_connection_string = 'mongodb://test_user:test_password@localhost:27017/test_database?authSource=admin'
    
    return config


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test."""
    # Reset MongoDB client singleton
    try:
        import youtube_elt.db
        youtube_elt.db._client = None
    except ImportError:
        pass
    
    yield
    
    # Cleanup after test
    try:
        import youtube_elt.db
        youtube_elt.db._client = None
    except ImportError:
        pass


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add unit marker to all tests by default
        if not any(marker.name in ['integration', 'slow'] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# Custom assertions
def assert_valid_timestamp(timestamp):
    """Assert that a timestamp is in valid ISO format."""
    import re
    pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'
    assert re.match(pattern, timestamp), f"Invalid timestamp format: {timestamp}"


def assert_valid_video_id(video_id):
    """Assert that a video ID is valid."""
    assert isinstance(video_id, str), "Video ID must be a string"
    assert len(video_id) > 0, "Video ID cannot be empty"
    assert len(video_id) <= 20, "Video ID too long"


# Add custom assertions to pytest namespace
pytest.assert_valid_timestamp = assert_valid_timestamp
pytest.assert_valid_video_id = assert_valid_video_id
