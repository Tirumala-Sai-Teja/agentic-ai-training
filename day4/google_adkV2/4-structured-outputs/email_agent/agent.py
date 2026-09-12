import os
from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from pydantic import BaseModel, Field
from google.adk.models.lite_llm import LiteLlm

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Using same model as other agents for consistency
# Updated to gemini-3.6-flash as gemini-2.0-flash is no longer available
model = LiteLlm(
    model="gemini/gemini-3.6-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
)

# Alternative: If you want to use Groq models (may have multi-turn issues)
# model = LiteLlm(model="groq/qwen/qwen3.6-27b", api_key=os.getenv("GROQ_API_KEY"))


# --- Define Output Schema ---
class EmailContent(BaseModel):
    subject: str = Field(
        description="The subject line of the email. Should be concise and descriptive."
    )
    body: str = Field(
        description="The main content of the email. Should be well-formatted with proper greeting, paragraphs, and signature."
    )


# --- Create Email Generator Agent ---
root_agent = LlmAgent(
    name="email_agent",
    #model="gemini-2.0-flash",
    model=model,
    instruction="""
        You are an Email Generation Assistant.
        Your task is to generate a professional email based on the user's request.

        GUIDELINES:
        - Create an appropriate subject line (concise and relevant)
        - Write a well-structured email body with:
            * Professional greeting
            * Clear and concise main content
            * Appropriate closing
            * Your name as signature
        - Suggest relevant attachments if applicable (empty list if none needed)
        - Email tone should match the purpose (formal for business, friendly for colleagues)
        - Keep emails concise but complete

        IMPORTANT: Your response MUST be valid JSON matching this structure:
        {
            "subject": "Subject line here",
            "body": "Email body here with proper paragraphs and formatting",
        }

        DO NOT include any explanations or additional text outside the JSON response.
    """,
    description="Generates professional emails with structured subject and body",
    output_schema=EmailContent,
    output_key="email",
)
