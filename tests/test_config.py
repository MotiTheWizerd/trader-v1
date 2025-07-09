"""
Tests for the configuration module.
"""
import os
import tempfile
from pathlib import Path

import pytest

from core.config import (
    PROJECT_ROOT,
    DATA_DIR,
    TICKERS_DIR,
    SIGNALS_DIR,
    LOGS_DIR,
    TICKER_DATA_DIR,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    get_ticker_data_path,
    get_signal_file_path,
    get_processed_data_path,
    get_log_file_path,
    settings,
    get_settings,
    load_env_file,
    get_env_variable,
)


def test_project_structure():
    """Test that the project structure is set up correctly."""
    # Check that all required directories exist
    assert PROJECT_ROOT.exists()
    assert PROJECT_ROOT.name == 'trader-v1'
    
    # Check that all required directories are Path objects
    assert isinstance(DATA_DIR, Path)
    assert isinstance(TICKERS_DIR, Path)
    assert isinstance(SIGNALS_DIR, Path)
    assert isinstance(LOGS_DIR, Path)
    assert isinstance(TICKER_DATA_DIR, Path)
    assert isinstance(PROCESSED_DATA_DIR, Path)
    assert isinstance(RAW_DATA_DIR, Path)
    
    # Check that data directories are subdirectories of the project root
    assert DATA_DIR.parent == PROJECT_ROOT
    assert TICKERS_DIR.parent == PROJECT_ROOT
    assert SIGNALS_DIR.parent == PROJECT_ROOT
    assert LOGS_DIR.parent == PROJECT_ROOT
    
    # Check that data subdirectories are correctly nested
    assert TICKER_DATA_DIR.parent == TICKERS_DIR
    assert PROCESSED_DATA_DIR.parent == DATA_DIR
    assert RAW_DATA_DIR.parent == DATA_DIR


def test_path_functions():
    """Test path generation functions."""
    # Test ticker data path
    ticker_path = get_ticker_data_path('AAPL', '20230101')
    assert ticker_path == TICKER_DATA_DIR / 'AAPL/20230101.csv'
    
    # Test signal file path
    signal_path = get_signal_file_path('AAPL', '20230101')
    assert signal_path == SIGNALS_DIR / 'AAPL_signals_20230101.parquet'
    
    # Test processed data path
    processed_path = get_processed_data_path('test.parquet')
    assert processed_path == PROCESSED_DATA_DIR / 'test.parquet'
    
    # Test log file path
    log_path = get_log_file_path('test')
    assert log_path == LOGS_DIR / 'test.log'


def test_settings():
    """Test settings loading and access."""
    # Check that settings is a dictionary
    assert isinstance(settings, dict)
    assert 'environment' in settings
    assert 'debug' in settings
    assert 'app_name' in settings
    assert 'version' in settings
    
    # Check get_settings function
    settings_dict = get_settings()
    assert isinstance(settings_dict, dict)
    assert settings_dict == settings


def test_env_vars(monkeypatch):
    """Test environment variable handling."""
    # Set up test environment variables
    test_vars = {
        'TEST_STRING': 'test_value',
        'TEST_INT': '42',
        'TEST_FLOAT': '3.14',
        'TEST_BOOL': 'true',
        'TEST_LIST': 'a,b,c',
    }
    
    for key, value in test_vars.items():
        monkeypatch.setenv(key, value)
    
    # Test string variable
    assert get_env_variable('TEST_STRING') == 'test_value'
    assert get_env_variable('TEST_STRING', default='default') == 'test_value'
    
    # Test type conversion
    assert get_env_variable('TEST_INT', default=0) == 42
    assert get_env_variable('TEST_FLOAT', default=0.0) == 3.14
    assert get_env_variable('TEST_BOOL', default=False) is True
    assert get_env_variable('TEST_LIST', default=[]) == ['a', 'b', 'c']
    
    # Test default values
    assert get_env_variable('NON_EXISTENT', default='default') == 'default'
    
    # Test required variables
    with pytest.raises(ValueError):
        get_env_variable('NON_EXISTENT', required=True)


def test_env_file_loading():
    """Test loading environment variables from a .env file."""
    # Create a temporary .env file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("TEST_VAR=test_value\n")
        f.write("TEST_NUMBER=42\n")
        env_file = f.name
    
    try:
        # Load the .env file
        assert load_env_file(env_file) is True
        
        # Check that the variables were loaded
        assert os.getenv('TEST_VAR') == 'test_value'
        assert os.getenv('TEST_NUMBER') == '42'
        
    finally:
        # Clean up
        if os.path.exists(env_file):
            os.unlink(env_file)


if __name__ == '__main__':
    pytest.main()
