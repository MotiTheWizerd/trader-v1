import asyncio
import logging
from google.genai import types
from google.genai.errors import ClientError
from ui.agent_response import (
    process_agent_response,
    display_thinking_indicator,
    display_agent_call_started,
    display_completion_message,
    display_fallback_response,
    display_missing_response,
    display_error_message,
    console
)

# Optionally silence underlying logger—but better to filter parts manually.
logging.getLogger("google_genai.types").setLevel(logging.ERROR)

async def call_agent_async(runner, user_id, session_id, message):
    display_agent_call_started(user_id, session_id, message)
    new_message = types.Content(role="user", parts=[types.Part(text=message)])
    overall_final_response = None

    thinking_task = asyncio.create_task(display_thinking_indicator())

    try:
        with console.status("[bold blue]🧠 Agent thinking...", spinner="dots") as status:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=new_message
            ):
                if thinking_task and not thinking_task.done():
                    thinking_task.cancel()
                    try:
                        await thinking_task
                    except asyncio.CancelledError:
                        pass
                status.update("[bold green]Processing agent responses...")

                # Handle tool/function calls
                if event.actions and getattr(event.actions, "function_call", None):
                    fc = event.actions.function_call
                    console.log(f" Tool via actions: {fc.name}, args: {fc.args}")
                    continue

                # Fallback if embedded in content parts
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "function_call", None):
                            fc = part.function_call
                            console.log(f"⚡ Tool via content part: {fc.name}, args: {fc.args}")
                            break

                # Process and display each event response
                # process_agent_response will return None if the event has no valid content to display
                response_text = await process_agent_response(event)
                
                # Skip further processing if this event had no valid content
                if response_text is None and not event.is_final_response():
                    continue
            
                # 📝 Build concatenated text only from actual text parts
                if event.content and event.content.parts:
                    text_parts = [part.text for part in event.content.parts if getattr(part, "text", None)]
                    concatenated = "".join(text_parts)

                    # 🟢 If this is final response, use it
                    if event.is_final_response():
                        if concatenated:
                            overall_final_response = concatenated
                        elif response_text:  # Use the processed response if available
                            overall_final_response = response_text
                        else:
                            display_missing_response()
                else:
                    if event.is_final_response():
                        display_missing_response()

        if thinking_task and not thinking_task.done():
            thinking_task.cancel()
            try:
                await thinking_task
            except asyncio.CancelledError:
                pass

        if overall_final_response:
            display_completion_message(success=True)
            return overall_final_response
        else:
            display_completion_message(success=False)
            return "Agent finished, but no final textual response was extracted."
    
    except ClientError as e:
        # Cancel the thinking indicator if it's still running
        if thinking_task and not thinking_task.done():
            thinking_task.cancel()
            try:
                await thinking_task
            except asyncio.CancelledError:
                pass
        
        # Check if this is a quota exceeded error
        error_str = str(e).lower()
        if "429" in error_str and "quota" in error_str:
            error_message = "⚠️ API quota exceeded. You've reached your current usage limit. Please try again later or upgrade your plan."
            display_error_message(error_message)
            return error_message
        else:
            # Handle other API errors gracefully
            error_message = f"⚠️ API error occurred: {str(e)}"
            display_error_message(error_message)
            return error_message
    
    except Exception as e:
        # Cancel the thinking indicator if it's still running
        if thinking_task and not thinking_task.done():
            thinking_task.cancel()
            try:
                await thinking_task
            except asyncio.CancelledError:
                pass
        
        # Handle any other unexpected errors
        error_message = f"⚠️ An unexpected error occurred: {str(e)}"
        display_error_message(error_message)
        return error_message
