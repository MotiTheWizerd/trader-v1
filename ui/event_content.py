"""
Event content processing and rendering components.
This module provides reusable components for processing and rendering event content.
"""
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich import box

# Initialize Rich console
console = Console()

async def process_event_content(event, part, is_final=False):
    """
    Process different types of content parts and return appropriate Rich renderable
    with special formatting for different content types
    
    Args:
        event: The event object
        part: The content part to process
        is_final: Whether this is the final response
        
    Returns:
        Rich renderable object for the content
    """
    
    if hasattr(part, "text") and part.text:
        display_text = part.text
        if len(display_text) > 1000 and not is_final:
            display_text = display_text[:1000] + "... [truncated]"
        
        # For final responses, use a special panel with a different style
        if is_final:
            return Panel(
                Markdown(display_text),
                title="[bold green]Final Response[/]",
                border_style="green",
                box=box.ROUNDED
            )
        # For regular text, use a simple panel
        return Panel(
            Text(display_text),
            title="[bold blue]Text Content[/]",
            border_style="blue"
        )
        
    elif hasattr(part, "executable_code") or hasattr(part, "tool_code"):
        # Get the code content from the appropriate attribute
        tool_code_attr = getattr(part, "tool_code", getattr(part, "executable_code", None))
        if tool_code_attr:
            return Panel(
                Syntax(tool_code_attr, "python", theme="monokai", line_numbers=True),
                title="[bold yellow]Tool/Executable Code[/]",
                border_style="yellow"
            )
            
    elif hasattr(part, "code_execution_result") or hasattr(part, "tool_response"):
        # Get the response content from the appropriate attribute
        tool_response_attr = getattr(part, "tool_response", getattr(part, "code_execution_result", None))
        if tool_response_attr:
            return Panel(
                Text(str(tool_response_attr)),
                title="[bold magenta]Tool Response/Execution Result[/]",
                border_style="magenta"
            )
            
    elif hasattr(part, "function_response") and part.function_response is not None:
        return Panel(
            Text(str(part.function_response)),
            title="[bold cyan]Function Response[/]",
            border_style="cyan"
        )
        
    # Default case if no specific content type is identified
    return Text("Unknown content type")
