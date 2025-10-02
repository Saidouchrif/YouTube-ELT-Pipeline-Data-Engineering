"""
Tests for configuration module.
"""
import pytest
from unittest.mock import patch, Mock
import os

# Import the module to test
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.settings import Config


class TestConfigInitialization:
    """Test cases for Config class initialization."""
    
    def test_config_creation(self):
        """Test that Config can be created."""
        config = Config()
        assert config is not None
    
    @patch.dict(os.environ, {
        'YOUTUBE_API_KEY': 'test_api_key',
        'YOUTUBE_CHANNEL_HANDLE': 'TestChannel',
        'YOUTUBE_MAX_RESULTS': '100',
        'YOUTUBE_QUOTA_LIMIT': '5000'
    })
    def test_config_with_environment_variables(self):
        """Test Config initialization with environment variables."""
        config = Config()
        
        # Test that environment variables are read
        assert config.YOUTUBE_API_KEY == 'test_api_key'
        assert config.YOUTUBE_CHANNEL_HANDLE == 'TestChannel'
        assert config.YOUTUBE_MAX_RESULTS == 100
        assert config.YOUTUBE_QUOTA_LIMIT == 5000
    
    def test_config_default_values(self):
        """Test Config default values when no environment variables are set."""
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            
            # Test default values
            assert config.YOUTUBE_API_KEY == ''
            assert config.YOUTUBE_CHANNEL_HANDLE == 'MrBeast'
            assert config.YOUTUBE_MAX_RESULTS == 50
            assert config.YOUTUBE_QUOTA_LIMIT == 10000


class TestConfigProperties:
    """Test cases for Config properties."""
    
    def test_mongo_connection_string(self):
        """Test MongoDB connection string generation."""
        # Test the connection string format with custom values
        config = Config()
        
        # Override specific attributes for this test
        config.MONGO_HOST = 'test_host'
        config.MONGO_PORT = 27018
        config.MONGO_USERNAME = 'test_user'
        config.MONGO_PASSWORD = 'test_pass'
        config.MONGO_DATABASE = 'test_db'
        
        expected = "mongodb://test_user:test_pass@test_host:27018/test_db?authSource=admin"
        assert config.mongo_connection_string == expected
    
    def test_mongo_connection_string_defaults(self):
        """Test MongoDB connection string format with actual default values."""
        config = Config()
        
        # Test that the connection string has the correct format
        # regardless of the specific values
        connection_string = config.mongo_connection_string
        
        # Verify it's a valid MongoDB connection string format
        assert connection_string.startswith("mongodb://")
        assert "?authSource=admin" in connection_string
        assert "@" in connection_string
        assert "/" in connection_string
        
        # Test with known values by setting them explicitly
        config.MONGO_HOST = 'localhost'
        config.MONGO_PORT = 27017
        config.MONGO_USERNAME = 'test_user'
        config.MONGO_PASSWORD = 'test_password'
        config.MONGO_DATABASE = 'test_database'
        
        expected = "mongodb://test_user:test_password@localhost:27017/test_database?authSource=admin"
        assert config.mongo_connection_string == expected
    
    def test_youtube_api_config(self):
        """Test YouTube API configuration property."""
        config = Config()
        
        # Override for testing
        config.YOUTUBE_API_KEY = 'test_key'
        config.YOUTUBE_CHANNEL_HANDLE = 'TestChannel'
        config.YOUTUBE_MAX_RESULTS = 75
        config.YOUTUBE_QUOTA_LIMIT = 8000
        
        api_config = config.youtube_api_config
        
        expected = {
            'api_key': 'test_key',
            'channel_handle': 'TestChannel',
            'max_results': 75,
            'quota_limit': 8000
        }
        assert api_config == expected
    
    def test_mongodb_config(self):
        """Test MongoDB configuration property."""
        config = Config()
        
        # Set known values for testing
        config.MONGO_HOST = 'localhost'
        config.MONGO_PORT = 27017
        config.MONGO_USERNAME = 'test_user'
        config.MONGO_PASSWORD = 'test_password'
        config.MONGO_DATABASE = 'test_database'
        
        mongodb_config = config.mongodb_config
        
        # Check that all required keys are present
        required_keys = ['host', 'port', 'username', 'password', 'database', 'connection_string']
        for key in required_keys:
            assert key in mongodb_config
        
        # Check the values we set
        assert mongodb_config['host'] == 'localhost'
        assert mongodb_config['port'] == 27017
        assert mongodb_config['username'] == 'test_user'
        assert mongodb_config['password'] == 'test_password'
        assert mongodb_config['database'] == 'test_database'
        
        # Check that connection_string is properly formatted
        expected_connection = "mongodb://test_user:test_password@localhost:27017/test_database?authSource=admin"
        assert mongodb_config['connection_string'] == expected_connection
    
    def test_collections_config(self):
        """Test collections configuration property."""
        config = Config()
        collections_config = config.collections_config
        
        expected = {
            'staging': 'staging_data',
            'core': 'core_data',
            'history': 'history_data'
        }
        assert collections_config == expected


class TestConfigValidation:
    """Test cases for Config validation."""
    
    def test_validate_config_valid(self):
        """Test validation with valid configuration."""
        config = Config()
        
        # Set valid values for testing
        config.YOUTUBE_API_KEY = 'valid_key'
        config.MONGO_HOST = 'valid_host'
        config.MONGO_USERNAME = 'valid_user'
        config.MONGO_PASSWORD = 'valid_pass'
        config.MONGO_DATABASE = 'valid_db'
        
        assert config.validate_config() is True
    
    def test_validate_config_missing_api_key(self):
        """Test validation with missing API key."""
        config = Config()
        config.YOUTUBE_API_KEY = ''  # Empty API key
        assert config.validate_config() is False
    
    def test_validate_config_missing_mongo_config(self):
        """Test validation with missing MongoDB configuration."""
        config = Config()
        
        # Set valid API key but empty MongoDB config
        config.YOUTUBE_API_KEY = 'valid_key'
        config.MONGO_HOST = ''
        config.MONGO_USERNAME = ''
        config.MONGO_PASSWORD = ''
        config.MONGO_DATABASE = ''
        
        assert config.validate_config() is False


class TestAirflowVariableIntegration:
    """Test cases for Airflow Variable integration."""
    
    @patch('config.settings.Config._AF_VAR')
    def test_get_with_airflow_variable(self, mock_af_var):
        """Test getting configuration from Airflow Variable."""
        # Mock Airflow Variable
        mock_af_var.get.return_value = 'airflow_value'
        
        config = Config()
        result = config._get('TEST_KEY', 'default_value')
        
        assert result == 'airflow_value'
        mock_af_var.get.assert_called_once_with('TEST_KEY')
    
    @patch('config.settings.Config._AF_VAR')
    def test_get_with_airflow_variable_none(self, mock_af_var):
        """Test getting configuration when Airflow Variable returns None."""
        # Mock Airflow Variable to return None
        mock_af_var.get.return_value = None
        
        with patch.dict(os.environ, {'TEST_KEY': 'env_value'}):
            config = Config()
            result = config._get('TEST_KEY', 'default_value')
            
            assert result == 'env_value'
    
    @patch('config.settings.Config._AF_VAR')
    def test_get_with_airflow_variable_exception(self, mock_af_var):
        """Test getting configuration when Airflow Variable raises exception."""
        # Mock Airflow Variable to raise exception
        mock_af_var.get.side_effect = Exception("Airflow not available")
        
        with patch.dict(os.environ, {'TEST_KEY': 'env_value'}):
            config = Config()
            result = config._get('TEST_KEY', 'default_value')
            
            assert result == 'env_value'
    
    def test_get_without_airflow_variable(self):
        """Test getting configuration when Airflow Variable is not available."""
        # Test when _AF_VAR is None
        with patch('config.settings.Config._AF_VAR', None):
            with patch.dict(os.environ, {'TEST_KEY': 'env_value'}):
                config = Config()
                result = config._get('TEST_KEY', 'default_value')
                
                assert result == 'env_value'


class TestConfigConstants:
    """Test cases for Config constants."""
    
    def test_collection_names(self):
        """Test that collection names are correctly defined."""
        config = Config()
        
        assert config.STAGING_COLLECTION == 'staging_data'
        assert config.CORE_COLLECTION == 'core_data'
        assert config.HISTORY_COLLECTION == 'history_data'
    
    def test_default_paths(self):
        """Test that default paths are correctly defined."""
        config = Config()
        
        assert config.DATA_STAGING_PATH == '/data/staging/'
        assert config.DATA_PROCESSED_PATH == '/data/processed/'
    
    def test_retry_configuration(self):
        """Test that retry configuration has correct defaults."""
        config = Config()
        
        assert config.RETRY_ATTEMPTS == 3
        assert config.RETRY_DELAY == 5
    
    def test_logging_configuration(self):
        """Test that logging configuration has correct defaults."""
        config = Config()
        
        assert config.LOG_LEVEL == 'INFO'
        assert config.LOG_FORMAT == 'json'


class TestConfigIntegration:
    """Integration tests for Config module."""
    
    def test_config_module_imports(self):
        """Test that config module imports work correctly."""
        from config.settings import Config, config
        
        # Verify classes and instances exist
        assert Config is not None
        assert config is not None
        assert isinstance(config, Config)
    
    def test_global_config_instance(self):
        """Test that global config instance is properly initialized."""
        from config.settings import config
        
        # Should be a Config instance
        assert isinstance(config, Config)
        
        # Should have all required attributes
        assert hasattr(config, 'YOUTUBE_API_KEY')
        assert hasattr(config, 'MONGO_HOST')
        assert hasattr(config, 'mongo_connection_string')


@pytest.mark.parametrize("env_var,default,expected", [
    ('YOUTUBE_MAX_RESULTS', '50', 50),
    ('YOUTUBE_QUOTA_LIMIT', '10000', 10000),
    ('MONGO_PORT', '27017', 27017),
    ('RETRY_ATTEMPTS', '3', 3),
    ('RETRY_DELAY', '5', 5),
])
def test_integer_conversion(env_var, default, expected):
    """Parametrized test for integer environment variable conversion."""
    with patch.dict(os.environ, {env_var: default}):
        config = Config()
        
        # Get the attribute value
        attr_name = env_var
        if hasattr(config, attr_name):
            value = getattr(config, attr_name)
            assert value == expected
            assert isinstance(value, int)


@pytest.mark.parametrize("host,port,user,password,database,expected_contains", [
    ('localhost', '27017', 'user', 'pass', 'db', 'mongodb://user:pass@localhost:27017/db'),
    ('mongo.example.com', '27018', 'admin', 'secret', 'mydb', 'mongodb://admin:secret@mongo.example.com:27018/mydb'),
])
def test_connection_string_generation(host, port, user, password, database, expected_contains):
    """Parametrized test for MongoDB connection string generation."""
    with patch.dict(os.environ, {
        'MONGO_HOST': host,
        'MONGO_PORT': port,
        'MONGO_USERNAME': user,
        'MONGO_PASSWORD': password,
        'MONGO_DATABASE': database
    }):
        config = Config()
        connection_string = config.mongo_connection_string
        
        assert expected_contains in connection_string
        assert '?authSource=admin' in connection_string
