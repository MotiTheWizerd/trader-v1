"""
User input handling and interaction components.
This module provides reusable components for handling user input in terminal applications.
"""
from rich.prompt import Confirm, Prompt, IntPrompt
from ui.components import MatrixPrompt

def get_user_input(prompt_text=None, matrix_style=True):
    """
    Get user input with optional Matrix styling
    
    Args:
        prompt_text: Custom prompt text (default: None)
        matrix_style: Whether to use Matrix-style prompt (default: True)
        
    Returns:
        User input string
    """
    if matrix_style:
        prompt = MatrixPrompt()
        return prompt.ask(prompt_text)
    else:
        return Prompt.ask(prompt_text or "> ")

def get_confirmation(prompt_text="Proceed?", default=True):
    """
    Get user confirmation (yes/no)
    
    Args:
        prompt_text: Prompt text to display
        default: Default value (True for yes, False for no)
        
    Returns:
        Boolean indicating user confirmation
    """
    return Confirm.ask(prompt_text, default=default)

def get_numeric_input(prompt_text="Enter a number:", minimum=None, maximum=None):
    """
    Get numeric input from user with optional range validation
    
    Args:
        prompt_text: Prompt text to display
        minimum: Minimum allowed value (inclusive)
        maximum: Maximum allowed value (inclusive)
        
    Returns:
        Integer value entered by user
    """
    return IntPrompt.ask(
        prompt_text,
        default=minimum or 0,
        show_default=minimum is not None,
        min_value=minimum,
        max_value=maximum
    )
