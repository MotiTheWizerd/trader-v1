import time
import uuid
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.spinner import Spinner
from rich import box

# Initialize Rich console
console = Console()

def create_event_layout():
    """
    Create a layout for organizing the display of agent events
    
    Returns:
        Layout object with configured sections for agent response
    """
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main")
    )
    layout["main"].split_row(
        Layout(name="content", ratio=3),
        Layout(name="metadata", ratio=1)
    )
    return layout

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
                box=box.ROUNDED,
                expand=True,  # Allow panel to expand to fit content
                height=None   # Don't restrict height, let it grow as needed
            )
        # For regular text, use a simple panel
        return Panel(
            Text(display_text),
            title="[bold blue]Text Content[/]",
            border_style="blue",
            expand=True,  # Allow panel to expand to fit content
            height=None   # Don't restrict height, let it grow as needed
        )
        
    elif hasattr(part, "executable_code") or hasattr(part, "tool_code"):
        # Get the code content from the appropriate attribute
        tool_code_attr = getattr(part, "tool_code", getattr(part, "executable_code", None))
        if tool_code_attr:
            return Panel(
                Syntax(tool_code_attr, "python", theme="monokai", line_numbers=True),
                title="[bold yellow]Tool/Executable Code[/]",
                border_style="yellow",
                expand=True,  # Allow panel to expand to fit content
                height=None   # Don't restrict height, let it grow as needed
            )
            
    elif hasattr(part, "code_execution_result") or hasattr(part, "tool_response"):
        # Get the response content from the appropriate attribute
        tool_response_attr = getattr(part, "tool_response", getattr(part, "code_execution_result", None))
        if tool_response_attr:
            return Panel(
                Text(str(tool_response_attr)),
                title="[bold magenta]Tool Response/Execution Result[/]",
                border_style="magenta",
                expand=True,  # Allow panel to expand to fit content
                height=None   # Don't restrict height, let it grow as needed
            )
            
    elif hasattr(part, "function_response") and part.function_response is not None:
        return Panel(
            Text(str(part.function_response)),
            title="[bold cyan]Function Response[/]",
            border_style="cyan",
            expand=True,  # Allow panel to expand to fit content
            height=None   # Don't restrict height, let it grow as needed
        )
        
    elif hasattr(part, "function_call") and part.function_call is not None:
        # Handle function_call parts with lightning emoji and "Tool call"
        function_call_info = str(part.function_call)
        
        # Extract additional information if available
        additional_info = ""
        if hasattr(part.function_call, "name"):
            additional_info += f"\nFunction: {part.function_call.name}"
        if hasattr(part.function_call, "args") and part.function_call.args:
            additional_info += f"\nArgs: {part.function_call.args}"
        
        display_text = f"⚡ Tool call{additional_info}" if additional_info else "⚡ Tool call"
        
        return Panel(
            Text(display_text),
            title="[bold yellow]⚡ Tool Call[/]",
            border_style="yellow"
        )
        
    # Default case if no specific content type is identified
    # Return None to indicate this part should be skipped
    return None

def create_metadata_table(event):
    """
    Create a table with event metadata including ID, author, status and timestamp
    
    Args:
        event: The event object
        
    Returns:
        Panel containing a table with event metadata
    """
    table = Table(box=box.SIMPLE)
    table.add_column("Property", style="bold")
    table.add_column("Value")
    
    table.add_row("Event ID", str(event.id))
    table.add_row("Author", str(event.author))
    table.add_row("Final", str(event.is_final_response()))
    table.add_row("Timestamp", time.strftime("%H:%M:%S"))
    
    return Panel(table, title="[bold white]Event Metadata[/]", border_style="white")

async def process_agent_response(event):
    """
    Process agent response events and display them using Rich components.
    Returns extracted text if the event is final.
    
    Args:
        event: The agent response event
        
    Returns:
        Extracted text if the event is final, otherwise None
    """
    # Create a unique ID for this event processing
    event_id = str(uuid.uuid4())[:8]
    
    # Create layout for this event
    layout = create_event_layout()
    
    # Set header
    layout["header"].update(
        Panel(
            Text(f"Agent Response (Event {event_id})", style="bold white"),
            border_style="white",
            box=box.SIMPLE
        )
    )
    
    # Process content parts
    content_renderables = []
    extracted_text_parts = []
    
    if event.content and event.content.parts:
        for part in event.content.parts:
            # Check if this is the final response to apply special formatting
            is_final = event.is_final_response()
            
            # Process this content part
            renderable = await process_event_content(event, part, is_final)
            
            # Only add renderable if it's not None (skip unknown content types)
            if renderable is not None:
                content_renderables.append(renderable)
            
            # If this is the final response and has text, extract it
            if is_final and hasattr(part, "text") and part.text:
                extracted_text_parts.append(part.text.strip())
    
    # Combine all extracted text parts
    extracted_text = "\n".join(extracted_text_parts) if extracted_text_parts else None
    
    # If no valid content parts, return early without displaying anything
    if not content_renderables:
        return None
    
    # Update the layout with content and metadata
    # Combine all renderables into a single display
    if len(content_renderables) == 1:
        content = content_renderables[0]
    elif len(content_renderables) > 1:
        # Create a combined display with all content parts
        from rich.columns import Columns
        content = Columns(content_renderables)
    else:
        # This shouldn't happen due to the early return above, but just in case
        return None
    
    layout["content"].update(Panel(
        content,
        title="[bold blue]Agent Response[/]",
        border_style="blue",
        box=box.ROUNDED,
        expand=True,  # Allow panel to expand to fit content
        height=None   # Don't restrict height, let it grow as needed
    ))
    layout["metadata"].update(create_metadata_table(event))
    
    # Display the complete layout
    console.print(layout)
    
    # Return extracted text if this was the final response
    return extracted_text

async def display_thinking_indicator():
    """
    Display a thinking indicator with brain emoji while the agent is thinking
    """
    spinner = Spinner("dots", "🧠 Thinking")
    with Live(spinner, refresh_per_second=10) as live:
        try:
            while True:
                spinner.update()
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            # Clean up when cancelled
            live.update(Text(""))
            raise

def display_agent_call_started(user_id, session_id, message):
    """
    Display the initial agent call information
    
    Args:
        user_id: The user ID
        session_id: The session ID
        message: The user message
    """
    console.print(Panel(
        f"Calling agent for User: [bold]{user_id}[/], Session: [bold]{session_id}[/]\nMessage: [italic]'{message}'[/]",
        title="[bold green]Agent Call Started[/]",
        border_style="green",
        box=box.DOUBLE,
        expand=True,  # Allow panel to expand to fit content
        height=None   # Don't restrict height, let it grow as needed
    ))

def display_completion_message(success=True):
    """
    Display agent execution completion message
    
    Args:
        success: Whether the execution was successful
    """
    if success:
        console.print(Panel(
            "[bold green]✅ Agent execution completed successfully[/]",
            box=box.SIMPLE,
            expand=True,
            height=None
        ))
    else:
        console.print(Panel(
            "[bold red]❌ Agent execution finished, but no clear overall final text response was captured.[/]",
            border_style="red",
            expand=True,
            height=None
        ))

def display_fallback_response(text):
    """
    Display the fallback final response when process_agent_response didn't pick it up
    
    Args:
        text: The response text
    """
    console.print(Panel(
        Markdown(text),
        title="[bold cyan]Final Response (Fallback)[/]",
        border_style="cyan",
        box=box.ROUNDED,
        expand=True,  # Allow panel to expand to fit content
        height=None   # Don't restrict height, let it grow as needed
    ))

def display_missing_response():
    """
    Display a message when no clear text was found in the final event
    """
    console.print(Panel(
        "Final event received, but no straightforward text found in its parts.\n"
        "The actual final data might have been in an earlier event.",
        title="[bold red]Missing Final Response[/]",
        border_style="red",
        expand=True,  # Allow panel to expand to fit content
        height=None   # Don't restrict height, let it grow as needed
    ))

def display_error_message(message):
    """
    Display an error message with distinctive styling
    
    Args:
        message: The error message to display
    """
    console.print(Panel(
        Text(message, style="bold red"),
        title="[bold red]Error[/]",
        border_style="red",
        box=box.DOUBLE_EDGE,
        expand=True,  # Allow panel to expand to fit content
        height=None   # Don't restrict height, let it grow as needed
    ))
