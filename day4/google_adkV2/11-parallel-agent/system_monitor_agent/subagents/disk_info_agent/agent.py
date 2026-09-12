"""
Disk Information Agent

This agent is responsible for gathering and analyzing disk information.
"""

import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from .tools import get_disk_info

# Load environment variables from parent .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

# Suppress Gemini LiteLLM warning since native integration is not available in this ADK version
os.environ["ADK_SUPPRESS_GEMINI_LITELLM_WARNINGS"] = "true"

# Using Gemini with a faster model for better performance
model = LiteLlm(
    model="gemini/gemini-3.5-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)

# Disk Information Agent
disk_info_agent = Agent(
    name="DiskInfoAgent",
    model=model,
    instruction="""You are a Disk Information Agent.
    
    When asked for system information, you should:
    1. Use the 'get_disk_info' tool to gather disk data
    2. Analyze the returned dictionary data
    3. Format this information into a concise, clear section of a system report
    
    The tool will return a dictionary with:
    - result: Core disk information including partitions
    - stats: Key statistical data about storage usage
    - additional_info: Context about the data collection
    
    Format your response as a well-structured report section with:
    - Partition information
    - Storage capacity and usage
    - Any storage concerns (high usage > 85%)
    
    IMPORTANT: You MUST call the get_disk_info tool. Do not make up information.
    """,
    description="Gathers and analyzes disk information",
    tools=[get_disk_info],
)
