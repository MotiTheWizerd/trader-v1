"""
Application settings and configuration.

This module handles runtime configuration, including environment variables
and application settings that can be overridden.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Environment detection
ENV = os.getenv('ENVIRONMENT', 'development')
DEBUG = ENV == 'development'
TESTING = ENV == 'testing'
PRODUCTION = ENV == 'production'

# Application settings
APP_NAME = "trader-v1"
VERSION = "0.1.0"

# API settings
API_PREFIX = "/api/v1"
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{Path(__file__).parent.parent}/data/trader.db")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# API Keys (use environment variables in production)
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# Cache settings
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes

def get_settings() -> Dict[str, Any]:
    """
    Get the current application settings as a dictionary.
    
    Returns:
        Dictionary containing all application settings
    """
    return {
        "environment": ENV,
        "debug": DEBUG,
        "testing": TESTING,
        "app_name": APP_NAME,
        "version": VERSION,
        "database_url": DATABASE_URL if not TESTING else TEST_DATABASE_URL,
        "log_level": LOG_LEVEL,
        "api_prefix": API_PREFIX,
        "cache_enabled": CACHE_ENABLED,
        "cache_ttl": CACHE_TTL,
    }

# Export settings
settings = get_settings()
