import os
from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from datetime import datetime
import requests

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Using current Gemini model through LiteLLM
# Updated to gemini-3.6-flash as gemini-2.0-flash is no longer available
model = LiteLlm(
    model="gemini/gemini-3.6-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)

# Other current Gemini model options through LiteLLM:
# model = LiteLlm(model="gemini/gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY"))
# model = LiteLlm(model="gemini/gemini-1.5-flash", api_key=os.getenv("GOOGLE_API_KEY"))

# Alternative: If you want to use Groq models (may have multi-turn issues with tools)
# model = LiteLlm(model="groq/qwen/qwen3.6-27b", api_key=os.getenv("GROQ_API_KEY"))

def get_current_time() -> dict:
    """
    Get the current time in the format YYYY-MM-DD HH:MM:SS
    """
    return {
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

def google_search(query: str) -> dict:
    """
    Search Google using SERP API
    """
    try:
        url = "https://serpapi.com/search?engine=google"
        params = {
            "q": query,
            "api_key": os.getenv("SERP_API_KEY"),
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Extract relevant results
        results = []
        if "organic_results" in data:
            for result in data["organic_results"][:5]:  # Get top 5 results
                results.append({
                    "title": result.get("title"),
                    "link": result.get("link"),
                    "snippet": result.get("snippet"),
                })
        
        return {
            "query": query,
            "results": results,
        }
    except Exception as e:
        return {
            "query": query,
            "error": str(e),
        }

root_agent = LlmAgent(
    name="tool_agent",
    model=model,
    description="Tool agent",
    instruction="""
    You are a helpful assistant that can use the following tools:
    - google_search: Search Google for information
    - get_current_time: Get the current date and time
    """,
    tools=[google_search, get_current_time],
)
