"""
Application-wide constants and configuration.

This module contains constants used throughout the application, such as
time periods, thresholds, and other configuration values.
"""
from datetime import timedelta

# Time periods
ONE_DAY = timedelta(days=1)
ONE_WEEK = timedelta(weeks=1)
ONE_MONTH = timedelta(days=30)
ONE_YEAR = timedelta(days=365)

# Signal generation
DEFAULT_LOOKBACK_PERIOD = 20  # Default lookback period for indicators
DEFAULT_THRESHOLD = 0.01  # Default threshold for signal generation

# Moving Average Signal Generation
WINDOW_CONF = 100  # Rolling window size for dynamic confidence calculation
Z_MIN = 1.0  # Minimum z-score for dynamic confidence threshold
QUANTILE_MIN = 0.90  # Minimum quantile for dynamic confidence threshold
USE_QUANTILE = False  # Whether to use quantile (True) or z-score (False) for dynamic threshold

# Data processing
CHUNK_SIZE = 1000  # Default chunk size for processing large datasets
BATCH_SIZE = 100  # Default batch size for database operations

# API and rate limiting
API_RATE_LIMIT = 200  # Max API calls per minute
API_RETRY_ATTEMPTS = 3  # Number of retry attempts for API calls
API_RETRY_DELAY = 5  # Delay between retry attempts in seconds

# Logging
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# File formats
SUPPORTED_FILE_FORMATS = ["csv", "parquet", "feather"]
DEFAULT_FILE_FORMAT = "parquet"

# Performance settings
MAX_WORKERS = 4  # Default number of worker threads/processes
