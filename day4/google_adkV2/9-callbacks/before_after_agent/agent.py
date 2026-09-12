"""
Before and After Agent Callbacks Example

This example demonstrates how to use both before_agent_callback and after_agent_callback 
for logging purposes.
"""

import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Suppress Gemini LiteLLM warning since native integration is not available in this ADK version
os.environ["ADK_SUPPRESS_GEMINI_LITELLM_WARNINGS"] = "true"

# Using Groq with a larger model for better performance (same as stateful multi-agent)
model = LiteLlm(
    model="gemini/gemini-3.6-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)



def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Simple callback that logs when the agent starts processing a request.

    Args:
        callback_context: Contains state and context information

    Returns:
        None to continue with normal agent processing
    """
    # Get the session state
    state = callback_context.state

    # Record timestamp
    timestamp = datetime.now()

    # Set agent name if not present
    if "agent_name" not in state:
        state["agent_name"] = "SimpleChatBot"

    # Initialize request counter
    if "request_counter" not in state:
        state["request_counter"] = 1
    else:
        state["request_counter"] += 1

    # Store start time for duration calculation in after_agent_callback
    state["request_start_time"] = timestamp.isoformat()

    # Log the request
    print("=== AGENT EXECUTION STARTED ===")
    print(f"Request #: {state['request_counter']}")
    print(f"Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

    # Print to console
    print(f"\n[BEFORE CALLBACK] Agent processing request #{state['request_counter']}")

    return None


def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Simple callback that logs when the agent finishes processing a request.

    Args:
        callback_context: Contains state and context information

    Returns:
        None to continue with normal agent processing
    """
    # Get the session state
    state = callback_context.state

    # Calculate request duration if start time is available
    timestamp = datetime.now()
    duration = None
    if "request_start_time" in state:
        start_time = datetime.fromisoformat(state["request_start_time"])
        duration = (timestamp - start_time).total_seconds()

    # Log the completion
    print("=== AGENT EXECUTION COMPLETED ===")
    print(f"Request #: {state.get('request_counter', 'Unknown')}")
    if duration is not None:
        print(f"Duration: {duration:.2f} seconds")

    # Print to console
    print(
        f"[AFTER CALLBACK] Agent completed request #{state.get('request_counter', 'Unknown')}"
    )
    if duration is not None:
        print(f"[AFTER CALLBACK] Processing took {duration:.2f} seconds")

    return None


# Create the Agent
root_agent = LlmAgent(
    name="before_after_agent",
    model=model,
    description="A basic agent that demonstrates before and after agent callbacks",
    instruction="""
    You are a friendly greeting agent. Your name is {agent_name}.
    
    Your job is to:
    - Greet users politely
    - Respond to basic questions
    - Keep your responses friendly and concise
    """,
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
)
