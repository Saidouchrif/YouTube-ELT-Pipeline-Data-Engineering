"""
Configuration settings for YouTube ELT Pipeline.

This module centralizes all configuration settings for the pipeline,
including API keys, database connections, and operational parameters.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Central configuration class for the YouTube ELT Pipeline."""
    
    # YouTube API Configuration
    # Try to import Airflow Variable lazily to avoid hard dependency at import time
    _AF_VAR = None
    try:
        from airflow.models import Variable as _AF_Variable  # type: ignore
        _AF_VAR = _AF_Variable
    except Exception:
        _AF_VAR = None

    @staticmethod
    def _get(key: str, default: str = "") -> str:
        """Get configuration value from Airflow Variable if available, else env."""
        if Config._AF_VAR is not None:
            try:
                val = Config._AF_VAR.get(key)
                if val is not None:
                    return str(val)
            except Exception:
                pass
        return os.getenv(key, default)

    YOUTUBE_API_KEY = _get('YOUTUBE_API_KEY', '')
    YOUTUBE_CHANNEL_HANDLE = _get('YOUTUBE_CHANNEL_HANDLE', 'MrBeast')
    YOUTUBE_MAX_RESULTS = int(_get('YOUTUBE_MAX_RESULTS', '50'))
    YOUTUBE_QUOTA_LIMIT = int(_get('YOUTUBE_QUOTA_LIMIT', '10000'))
    
    # MongoDB Configuration
    MONGO_HOST = os.getenv('MONGO_HOST', 'mongodb')
    MONGO_PORT = int(os.getenv('MONGO_PORT', '27017'))
    MONGO_USERNAME = os.getenv('MONGO_USERNAME', 'admin')
    MONGO_PASSWORD = os.getenv('MONGO_PASSWORD', 'password123')
    MONGO_DATABASE = os.getenv('MONGO_DATABASE', 'youtube_data')
    
    # Collection Names
    STAGING_COLLECTION = 'staging_data'
    CORE_COLLECTION = 'core_data'
    HISTORY_COLLECTION = 'history_data'
    
    # Data Storage Paths
    DATA_STAGING_PATH = os.getenv('DATA_STAGING_PATH', '/data/staging/')
    DATA_PROCESSED_PATH = os.getenv('DATA_PROCESSED_PATH', '/data/processed/')
    
    # Retry Configuration
    RETRY_ATTEMPTS = int(os.getenv('RETRY_ATTEMPTS', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', 'json')
    
    # Soda Configuration
    SODA_CORE_CONFIG_PATH = os.getenv('SODA_CORE_CONFIG_PATH', '/usr/local/airflow/config/soda_config.yml')
    
    @property
    def mongo_connection_string(self) -> str:
        """Generate MongoDB connection string."""
        return f"mongodb://{self.MONGO_USERNAME}:{self.MONGO_PASSWORD}@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DATABASE}"
    
    @property
    def youtube_api_config(self) -> Dict[str, Any]:
        """Get YouTube API configuration."""
        return {
            'api_key': self.YOUTUBE_API_KEY,
            'channel_handle': self.YOUTUBE_CHANNEL_HANDLE,
            'max_results': self.YOUTUBE_MAX_RESULTS,
            'quota_limit': self.YOUTUBE_QUOTA_LIMIT
        }
    
    @property
    def mongodb_config(self) -> Dict[str, Any]:
        """Get MongoDB configuration."""
        return {
            'host': self.MONGO_HOST,
            'port': self.MONGO_PORT,
            'username': self.MONGO_USERNAME,
            'password': self.MONGO_PASSWORD,
            'database': self.MONGO_DATABASE,
            'connection_string': self.mongo_connection_string
        }
    
    @property
    def collections_config(self) -> Dict[str, str]:
        """Get collection names configuration."""
        return {
            'staging': self.STAGING_COLLECTION,
            'core': self.CORE_COLLECTION,
            'history': self.HISTORY_COLLECTION
        }
    
    def validate_config(self) -> bool:
        """
        Validate that all required configuration is present.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        required_configs = [
            self.YOUTUBE_API_KEY,
            self.MONGO_HOST,
            self.MONGO_USERNAME,
            self.MONGO_PASSWORD,
            self.MONGO_DATABASE
        ]
        
        return all(config for config in required_configs)

# Global configuration instance
config = Config()
