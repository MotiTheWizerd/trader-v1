"""
Logging utilities for the scheduler.

This module provides structured logging for scheduler operations.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.logging import RichHandler

# Initialize rich console
console = Console()


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging with rich formatting and JSON file output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                show_time=False,
            ),
            logging.FileHandler(
                log_dir / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log",
                mode="a",
                encoding="utf-8",
            ),
        ],
    )
    
    # Configure JSON logging to a separate file
    json_handler = logging.FileHandler(
        log_dir / f"scheduler_{datetime.now().strftime('%Y%m%d')}.jsonl",
        mode="a",
        encoding="utf-8",
    )
    json_handler.setFormatter(JSONFormatter())
    logging.getLogger("scheduler").addHandler(json_handler)


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON strings."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


def log_job_start(job_name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Log the start of a job.
    
    Args:
        job_name: Name of the job being started
        metadata: Additional metadata to include in the log
    """
    log_data = {"event": "job_started", "job": job_name}
    if metadata:
        log_data.update(metadata)
    logging.info("Job started", extra={"data": log_data})


def log_job_end(job_name: str, status: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Log the end of a job.
    
    Args:
        job_name: Name of the job that ended
        status: Job status (e.g., 'completed', 'failed')
        metadata: Additional metadata to include in the log
    """
    log_data = {"event": "job_ended", "job": job_name, "status": status}
    if metadata:
        log_data.update(metadata)
    logging.info("Job ended", extra={"data": log_data})


def log_error(job_name: str, error: Exception, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Log an error that occurred during job execution.
    
    Args:
        job_name: Name of the job where the error occurred
        error: The exception that was raised
        metadata: Additional metadata to include in the log
    """
    log_data = {
        "event": "job_error",
        "job": job_name,
        "error_type": error.__class__.__name__,
        "error_message": str(error),
    }
    if metadata:
        log_data.update(metadata)
    logging.error("Job error", extra={"data": log_data}, exc_info=True)
