import os
from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
import requests

# Load environment variables from base path
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

# Using current Gemini model through LiteLLM
# Updated to gemini-3.6-flash as gemini-2.0-flash is no longer available
model = LiteLlm(
    model="gemini/gemini-3.6-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)


def search_news(query: str) -> str:
    """Search for news articles using SERP API."""
    try:
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": os.getenv("SERP_API_KEY"),
            "engine": "google",
            "tbm": "nws",  # News search
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract news results
        results = []
        if "news_results" in data:
            for result in data["news_results"][:5]:  # Get top 5 news articles
                results.append({
                    "title": result.get("title"),
                    "link": result.get("link"),
                    "source": result.get("source"),
                    "date": result.get("date"),
                    "snippet": result.get("snippet"),
                })
        
        if not results:
            return f"No news articles found for: {query}"
        
        # Format results as a readable string
        formatted = f"News articles for '{query}':\n"
        for i, r in enumerate(results, 1):
            formatted += f"\n{i}. {r['title']}\n"
            formatted += f"   Source: {r['source']}\n"
            formatted += f"   Date: {r['date']}\n"
            formatted += f"   Link: {r['link']}\n"
            if r['snippet']:
                formatted += f"   {r['snippet']}\n"
        return formatted
        
    except Exception as e:
        return f"Error searching news: {str(e)}"

news_analyst = LlmAgent(
    name="news_analyst",
    model=model,
    description="News analyst agent that searches and analyzes news articles",
    instruction="""
    You are a helpful news analyst assistant. When the user asks about news or current events,
    use the search_news tool to find relevant news articles and provide a comprehensive summary.
    """,
    tools=[search_news],
)
