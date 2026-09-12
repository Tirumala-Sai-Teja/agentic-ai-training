"""
CPU Information Agent

This agent is responsible for gathering and analyzing CPU information.
"""

import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from .tools import get_cpu_info

# Load environment variables from parent .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

# Suppress Gemini LiteLLM warning since native integration is not available in this ADK version
os.environ["ADK_SUPPRESS_GEMINI_LITELLM_WARNINGS"] = "true"

# Using Gemini with a faster model for better performance
model = LiteLlm(
    model="gemini/gemini-3.5-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)

# CPU Information Agent
cpu_info_agent = Agent(
    name="CpuInfoAgent",
    model=model,
    instruction="""You are a CPU Information Agent.
    
    When asked for system information, you should:
    1. Use the 'get_cpu_info' tool to gather CPU data
    2. Analyze the returned dictionary data
    3. Format this information into a concise, clear section of a system report
    
    The tool will return a dictionary with:
    - result: Core CPU information
    - stats: Key statistical data about CPU usage
    - additional_info: Context about the data collection
    
    Format your response as a well-structured report section with:
    - CPU core information (physical vs logical)
    - CPU usage statistics
    - Any performance concerns (high usage > 80%)
    
    IMPORTANT: You MUST call the get_cpu_info tool. Do not make up information.
    """,
    description="Gathers and analyzes CPU information",
    tools=[get_cpu_info],
)
