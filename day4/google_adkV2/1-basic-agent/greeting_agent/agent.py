import os
from dotenv import load_dotenv

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# https://docs.litellm.ai/docs/providers/groq
# Using standard Qwen model - should be more compatible with ADK v2
model = LiteLlm(
    model="groq/qwen/qwen3.6-27b",
    api_key=os.getenv("GROQ_API_KEY"),
)

root_agent = LlmAgent(
    name="greeting_agent",
    # https://ai.google.dev/gemini-api/docs/models
    #model="gemini-2.0-flash",
    model=model,
    description="Greeting agent",
    instruction="""
    You are a helpful assistant that greets the user. 
    Ask for the user's name and greet them by name.
    """,
    output_key="greeting_response",
)
