"""
LinkedIn Post Generator Root Agent

This module defines the root agent for the LinkedIn post generation application.
It uses sub-agents for initial generation, review, and refinement with an iterative process.
"""

import os
from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from .subagents.post_generator import initial_post_generator
from .subagents.post_refiner import post_refiner
from .subagents.post_reviewer import post_reviewer

# Load environment variables from parent .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Suppress Gemini LiteLLM warning since native integration is not available in this ADK version
os.environ["ADK_SUPPRESS_GEMINI_LITELLM_WARNINGS"] = "true"

# Using Gemini with a faster model for better performance
model = LiteLlm(
    model="gemini/gemini-3.5-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)

# Create the LinkedIn Post Generation Pipeline
root_agent = LlmAgent(
    name="LinkedInPostGenerationPipeline",
    model=model,
    description="Generates and refines a LinkedIn post through an iterative review process",
    instruction="""
    You are a LinkedIn Post Generation Pipeline Manager that coordinates three specialized agents:
    
    1. Initial Post Generator - creates the initial LinkedIn post about ADK tutorial
    2. Post Reviewer - evaluates post quality and provides feedback or exits if requirements met
    3. Post Refiner - improves the post based on review feedback
    
    When a user requests a LinkedIn post:
    - First, delegate to the initial post generator to create the draft
    - Then, delegate to the post reviewer to evaluate quality
    - If the reviewer provides feedback (doesn't exit loop), delegate to the post refiner to improve
    - Continue the review/refine cycle until the reviewer exits the loop
    - Present the final approved post to the user
    
    The refinement loop should continue iteratively until quality requirements are met (up to 10 iterations).
    Always track the current post state and review feedback throughout the process.
    """,
    sub_agents=[initial_post_generator, post_reviewer, post_refiner],
)
