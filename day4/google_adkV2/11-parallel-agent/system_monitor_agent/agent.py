"""
System Monitor Root Agent

This module defines the root agent for the system monitoring application.
It uses sub-agents for system information gathering and a synthesizer
for creating comprehensive reports.
"""

import os
from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from .subagents.cpu_info_agent import cpu_info_agent
from .subagents.disk_info_agent import disk_info_agent
from .subagents.memory_info_agent import memory_info_agent
from .subagents.synthesizer_agent import system_report_synthesizer

# Load environment variables from parent .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Suppress Gemini LiteLLM warning since native integration is not available in this ADK version
os.environ["ADK_SUPPRESS_GEMINI_LITELLM_WARNINGS"] = "true"

# Using Gemini with a faster model for better performance
model = LiteLlm(
    model="gemini/gemini-3.5-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)

# --- Create System Monitor Agent that coordinates the sub-agents ---
root_agent = LlmAgent(
    name="system_monitor_agent",
    model=model,
    description="A system monitoring agent that coordinates parallel information gathering and synthesis",
    instruction="""
    You are a System Monitor Coordinator that manages three specialized agents:
    
    1. CPU Information Agent - gathers and analyzes CPU data
    2. Memory Information Agent - gathers and analyzes memory data  
    3. Disk Information Agent - gathers and analyzes disk storage data
    4. System Report Synthesizer - combines all information into a comprehensive report
    
    When a user asks for system information:
    - Delegate to all three information gathering agents (CPU, Memory, Disk) in parallel
    - Once all information is gathered, delegate to the synthesizer to create a comprehensive report
    - Present the final synthesized report to the user
    
    Always coordinate the workflow to ensure all system components are analyzed before synthesis.
    """,
    sub_agents=[cpu_info_agent, memory_info_agent, disk_info_agent, system_report_synthesizer],
)
