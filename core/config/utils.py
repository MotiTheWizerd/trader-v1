"""
Utility functions for configuration management.

This module provides helper functions for working with configuration,
including environment variables, type conversion, and validation.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union

from dotenv import load_dotenv

T = TypeVar('T')

def load_env_file(env_file: Union[str, Path] = None) -> bool:
    """
    Load environment variables from a .env file.
    
    Args:
        env_file: Path to the .env file. If None, looks for .env in the project root.
        
    Returns:
        bool: True if the file was loaded successfully, False otherwise
    """
    if env_file is None:
        # Default to .env in the project root
        env_file = Path(__file__).parent.parent.parent / '.env'
    
    env_path = Path(env_file)
    if env_path.exists():
        return load_dotenv(dotenv_path=env_path, override=True)
    return False

def get_env_variable(name: str, default: T = None, required: bool = False) -> Optional[T]:
    """
    Get an environment variable with type conversion.
    
    Args:
        name: Name of the environment variable
        default: Default value if the variable is not set
        required: If True, raises an error if the variable is not set
        
    Returns:
        The value of the environment variable, converted to the type of default
        
    Raises:
        ValueError: If the variable is required but not set
    """
    value = os.getenv(name)
    
    if value is None:
        if required and default is None:
            raise ValueError(f"Required environment variable {name} is not set")
        return default
    
    # If no default is provided, return the raw string
    if default is None:
        return value
    
    # Convert the value to the type of the default
    return_type = type(default)
    
    try:
        if return_type == bool:
            # Handle boolean values
            return value.lower() in ('true', '1', 't', 'y', 'yes')
        elif return_type == list:
            # Handle comma-separated lists
            return [item.strip() for item in value.split(',')]
        elif return_type == dict:
            # Handle JSON-encoded dictionaries
            return json.loads(value)
        else:
            # Handle other types (int, float, str, etc.)
            return return_type(value)
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        if required:
            raise ValueError(f"Failed to parse environment variable {name}: {e}")
        return default

def get_config_path() -> Path:
    """
    Get the path to the configuration directory.
    
    Returns:
        Path to the configuration directory
    """
    return Path(__file__).parent

def get_project_root() -> Path:
    """
    Get the path to the project root directory.
    
    Returns:
        Path to the project root
    """
    return Path(__file__).parent.parent.parent
