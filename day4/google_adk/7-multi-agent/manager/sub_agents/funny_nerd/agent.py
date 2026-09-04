import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

# Load environment variables from base path
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

# Initialize Groq model with better model
model = LiteLlm(
    model="gemini/gemini-3.5-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)



def get_nerd_joke(topic: str) -> str:
    """Get a nerdy joke about a specific topic."""
    print(f"--- Tool: get_nerd_joke called for topic: {topic} ---")

    # Example jokes
    jokes = {
        "python": "Why don't Python programmers like to use inheritance? Because they don't like to inherit anything!",
        "javascript": "Why did the JavaScript developer go broke? Because he used up all his cache!",
        "java": "Why do Java developers wear glasses? Because they can't C#!",
        "programming": "Why do programmers prefer dark mode? Because light attracts bugs!",
        "math": "Why was the equal sign so humble? Because he knew he wasn't less than or greater than anyone else!",
        "physics": "Why did the photon check a hotel? Because it was travelling light!",
        "chemistry": "Why did the acid go to the gym? To become a buffer solution!",
        "biology": "Why did the cell go to therapy? Because it had too many issues!",
        "default": "Why did the computer go to the doctor? Because it had a virus!",
    }

    joke = jokes.get(topic.lower(), jokes["default"])
    return f"Here's a nerdy joke about {topic}: {joke}"


# Create the funny nerd agent
funny_nerd = Agent(
    name="funny_nerd",
    model=model,
    description="An agent that tells nerdy jokes about various topics.",
    instruction="""
    You are a funny nerd agent that tells nerdy jokes about various topics.
    
    When the user asks for a joke, use the get_nerd_joke tool with the topic they're interested in.
    If no topic is mentioned, suggest some: python, javascript, java, programming, math, physics, chemistry, biology.
    
    Always include the joke in your response.
    """,
    tools=[get_nerd_joke],
)
