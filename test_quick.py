#!/usr/bin/env python3
"""
Quick test script to verify our fixes work.
"""
import os
import sys
from unittest.mock import patch

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'plugins'))
sys.path.insert(0, os.path.dirname(__file__))

def test_config_fix():
    """Test that config works without Airflow Variables."""
    print("Testing config fix...")
    
    # Set up test environment
    test_env = {
        'MONGO_HOST': 'test_host',
        'MONGO_PORT': '27018',
        'MONGO_USERNAME': 'test_user',
        'MONGO_PASSWORD': 'test_pass',
        'MONGO_DATABASE': 'test_db'
    }
    
    with patch.dict(os.environ, test_env), \
         patch('config.settings.Config._AF_VAR', None):
        
        from config.settings import Config
        config = Config()
        
        expected = "mongodb://test_user:test_pass@test_host:27018/test_db?authSource=admin"
        actual = config.mongo_connection_string
        
        print(f"Expected: {expected}")
        print(f"Actual:   {actual}")
        
        if actual == expected:
            print("✅ Config test PASSED")
            return True
        else:
            print("❌ Config test FAILED")
            return False

if __name__ == "__main__":
    success = test_config_fix()
    sys.exit(0 if success else 1)
