"""
UI module for the trading prediction system.
Contains components for displaying data in the terminal using rich.
"""
from ui.data_display import (
    display_download_progress,
    display_download_summary,
    display_ticker_data_preview,
    display_error,
)

__all__ = [
    "display_download_progress",
    "display_download_summary",
    "display_ticker_data_preview",
    "display_error",
]
