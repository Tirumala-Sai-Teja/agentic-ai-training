"""
System Report Synthesizer Agent

This agent is responsible for synthesizing information from other agents
to create a comprehensive system health report.
"""

import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

# Load environment variables from parent .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

# Suppress Gemini LiteLLM warning since native integration is not available in this ADK version
os.environ["ADK_SUPPRESS_GEMINI_LITELLM_WARNINGS"] = "true"

# Using Gemini with a faster model for better performance
model = LiteLlm(
    model="gemini/gemini-3.5-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)

# System Report Synthesizer Agent
system_report_synthesizer = Agent(
    name="SystemReportSynthesizer",
    model=model,
    instruction="""You are a System Report Synthesizer.
    
    Your task is to create a comprehensive system health report by combining information from the previous agents that gathered CPU, memory, and disk information.
    
    Create a well-formatted report with:
    1. An executive summary at the top with overall system health status
    2. Sections for each component (CPU, Memory, Disk) with their respective information
    3. Recommendations based on any concerning metrics
    
    Use markdown formatting to make the report readable and professional.
    Highlight any concerning values and provide practical recommendations.
    
    Consider the context and information provided by the previous agents when creating your synthesis.
    """,
    description="Synthesizes all system information into a comprehensive report",
)
