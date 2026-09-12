"""
Sequential Agent with a Minimal Callback

This example demonstrates a lead qualification pipeline with a minimal
before_agent_callback that only initializes state once at the beginning.
"""

import os
from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from .subagents.recommender import action_recommender_agent
from .subagents.scorer import lead_scorer_agent

# Import the subagents
from .subagents.validator import lead_validator_agent

# Load environment variables from parent .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Suppress Gemini LiteLLM warning since native integration is not available in this ADK version
os.environ["ADK_SUPPRESS_GEMINI_LITELLM_WARNINGS"] = "true"

# Using Gemini with a faster model for better performance
model = LiteLlm(
    model="gemini/gemini-3.5-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)

# Create the sequential agent with minimal callback
root_agent = LlmAgent(
    name="LeadQualificationPipeline",
    model=model,
    sub_agents=[lead_validator_agent, lead_scorer_agent, action_recommender_agent],
    description="A pipeline that validates, scores, and recommends actions for sales leads",
    instruction="""
    You are a lead qualification pipeline manager that coordinates three specialized agents:
    
    1. Lead Validator Agent - validates if lead information is complete
    2. Lead Scorer Agent - scores qualified leads on a scale of 1-10
    3. Action Recommender Agent - recommends next actions based on scoring
    
    When a user provides lead information, delegate to the appropriate agents in sequence:
    - First, delegate to the validator to check if the lead is complete
    - If valid, delegate to the scorer to assess the lead quality
    - Finally, delegate to the recommender to suggest next actions
    
    Always present the final results in a clear, organized format showing all three stages.
    """,
)
