import os
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv

# Load environment variables from the .env file in this directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Suppress Gemini LiteLLM warning since native integration is not available in this ADK version
os.environ["ADK_SUPPRESS_GEMINI_LITELLM_WARNINGS"] = "true"

# Using Gemini via LiteLLM (native integration not available in this ADK version)
model = LiteLlm(
    model="gemini/gemini-3.6-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)

# Alternative: If you want to use Groq models (may have multi-turn issues)
# model = LiteLlm(model="groq/qwen/qwen3.6-27b", api_key=os.getenv("GROQ_API_KEY"))

# Create the root agent with ADK v2
root_agent = LlmAgent(
    name="question_answering_agent",
    model=model,
    description="Question answering agent with session context",
    instruction="""
    You are a helpful assistant that answers questions about the user's preferences.

    Here is some information about the user:
    Name: {user_name}
    Preferences: {user_preferences}

    Use this information to answer questions about the user. If the user provides their name or preferences, remember them for future conversations.
    """,
    output_key="answer",
)
