import os
import random
from dotenv import load_dotenv

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Using same model as tool agent for consistency
# Updated to gemini-3.6-flash as gemini-2.0-flash is no longer available
model = LiteLlm(
    model="gemini/gemini-3.6-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)

# Alternative: If you want to use Groq models (may have multi-turn issues with tools)
# model = LiteLlm(model="groq/qwen/qwen3.6-27b", api_key=os.getenv("GROQ_API_KEY"))


def get_dad_joke() -> str:
    """
    Get a random dad joke to tell the user.
    Returns a funny dad joke.
    """
    jokes = [
        "Why did the chicken cross the road? To get to the other side!",
        "What do you call a belt made of watches? A waist of time.",
        "What do you call fake spaghetti? An impasta!",
        "Why did the scarecrow win an award? Because he was outstanding in his field!",
    ]
    return random.choice(jokes)


root_agent = LlmAgent(
    name="dad_joke_agent",
    model=model,
    description="Dad joke agent",
    instruction="""
    You are a helpful assistant that can tell dad jokes. 
    When the user asks for a joke, use the `get_dad_joke` tool to get a joke and then share it with the user.
    Always include the joke result in your response to the user.
    """,
    tools=[get_dad_joke],
)
