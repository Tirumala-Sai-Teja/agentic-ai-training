"""
Classification Agent - Classifies documents as Cease, Uncertain, or Irrelevant
"""
import json
import re
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from src.config.config import GROQ_API_KEY, MODEL_NAME
from src.tools.audit_logger import get_audit_trail

logger = logging.getLogger(__name__)

# System prompt for document classification
CLASSIFICATION_SYSTEM_PROMPT = """You are a legal document classification expert. Your task is to analyze documents and classify them as either CEASE, UNCERTAIN, or IRRELEVANT.

CLASSIFICATION RULES:
- CEASE: Document contains clear demands to stop contact, cease communications, or revoke consent. Look for phrases like "stop calling", "cease and desist", "do not contact", "revoke consent".
- UNCERTAIN: Document has ambiguous intent, legal threats without clear stop commands, or is partially illegible.
- IRRELEVANT: Standard business correspondence, address changes, payment inquiries, or promotional materials.

IMPORTANT: Return ONLY valid JSON with this exact format:
{
  "classification": "Cease" or "Uncertain" or "Irrelevant",
  "confidence": 0.0 to 1.0,
  "explanation": "brief explanation",
  "key_indicators": ["phrase1", "phrase2"],
  "extracted_details": {
    "sender": "name or null",
    "key_phrases": ["phrase1", "phrase2"],
    "requested_action": "action or null",
    "deadline": "date or null"
  }
}

Be specific and base your classification only on the document content provided."""


class ExtractedDetails(BaseModel):
    """Extracted details from the document"""
    sender: Optional[str] = Field(default=None, description="Sender or organization name")
    key_phrases: Optional[list] = Field(default=None, description="Important phrases or demands")
    requested_action: Optional[str] = Field(default=None, description="What action is being requested")
    deadline: Optional[str] = Field(default=None, description="Any deadline mentioned")
    other_details: Optional[Dict[str, Any]] = Field(default=None, description="Other relevant details")


class ClassificationResult(BaseModel):
    """Classification result model"""
    document_name: str = Field(description="Name of the document")
    date_received: datetime = Field(description="Date and time when the document was received")
    classification: str = Field(description="One of: Cease, Uncertain, Irrelevant")
    confidence: float = Field(description="Confidence score between 0 and 1")
    explanation: str = Field(description="Detailed explanation for the classification")
    key_indicators: list = Field(description="Key indicators found in the document")
    extracted_details: ExtractedDetails = Field(description="Extracted details from the document")


class ClassificationAgent:
    """Agent responsible for classifying documents"""

    def __init__(self, llm_client=None):
        """
        Initialize the classification agent
        
        Args:
            llm_client: LLM client (optional, injected by manager)
        """
        if llm_client is None:
            if not GROQ_API_KEY:
                raise ValueError("Missing GROQ_API_KEY environment variable for LLM classification")
            self.llm_client = ChatGroq(
                api_key=GROQ_API_KEY,
                model_name=MODEL_NAME or "llama-3.3-70b-versatile",  # Default to a reliable, currently supported model
                temperature=0.1,  # Lower temperature for more consistent results
                max_tokens=1024,  # Limit response length
                top_p=0.9,  # Slightly more focused responses
                streaming=False
            )
        else:
            self.llm_client = llm_client

        self.audit_trail = get_audit_trail()
        self.name = "ClassificationAgent"


    def classify_with_llm(
        self,
        document_name: str,
        content: str,
        date_received: datetime
    ) -> ClassificationResult:
        """
        Classify using the LLM with system prompt guidance

        Args:
            document_name: Name of the document
            content: Document content
            date_received: When the document was received

        Returns:
            ClassificationResult with metadata and extracted details
        """
        if not self.llm_client:
            raise ValueError("LLM client is not configured for classification")

        # Create messages with system prompt and user content
        messages = [
            SystemMessage(content=CLASSIFICATION_SYSTEM_PROMPT),
            HumanMessage(content=f"""Please classify and extract details from the following document:

Document Name: {document_name}

---DOCUMENT CONTENT START---
{content}
---DOCUMENT CONTENT END---

Return ONLY the JSON object with classification, explanation, key_indicators, and extracted_details. No additional text.""")
        ]

        try:
            llm_response = self.llm_client.invoke(messages)
            response_text = getattr(llm_response, "content", None) or str(llm_response)
            response_text = response_text.strip()

            # Clean up response text - remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            # Extract JSON from response
            json_text = response_text
            if not json_text.startswith("{"):
                # Try to find JSON object in the response
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}") + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_text = response_text[start_idx:end_idx]

            parsed = json.loads(json_text)

            # Validate and sanitize classification
            classification = str(parsed.get("classification", "Uncertain")).strip().capitalize()
            if classification not in ["Cease", "Uncertain", "Irrelevant"]:
                logger.warning(f"Invalid classification '{classification}' from LLM, defaulting to Uncertain")
                classification = "Uncertain"

            # Validate and sanitize confidence - ensure it's never 0.0 for valid classifications
            confidence = float(parsed.get("confidence", 0.5))
            confidence = min(max(confidence, 0.0), 1.0)

            # If confidence is 0.0 but we have a valid classification, set minimum confidence
            if confidence == 0.0 and classification in ["Cease", "Uncertain", "Irrelevant"]:
                confidence = 0.7  # Default minimum confidence for valid classifications
                logger.info(f"Adjusted confidence from 0.0 to {confidence} for {classification} classification")

            # Get explanation
            explanation = str(parsed.get("explanation", "No explanation provided")).strip()
            if not explanation or explanation == "No explanation provided":
                explanation = f"Document classified as {classification} based on content analysis"

            # Get key indicators
            key_indicators = parsed.get("key_indicators", [])
            if not isinstance(key_indicators, list):
                key_indicators = [str(key_indicators)] if key_indicators else []

            # If no key indicators but we have a classification, add default ones
            if not key_indicators and classification == "Cease":
                key_indicators = ["Contains cease and desist language"]
            elif not key_indicators and classification == "Irrelevant":
                key_indicators = ["Standard business correspondence"]

            # Extract details from the LLM response
            extracted_details_raw = parsed.get("extracted_details", {})
            if not isinstance(extracted_details_raw, dict):
                extracted_details_raw = {}

            extracted_details = ExtractedDetails(
                sender=extracted_details_raw.get("sender"),
                key_phrases=extracted_details_raw.get("key_phrases", []),
                requested_action=extracted_details_raw.get("requested_action"),
                deadline=extracted_details_raw.get("deadline")
            )

            return ClassificationResult(
                document_name=document_name,
                date_received=date_received,
                classification=classification,
                confidence=confidence,
                explanation=explanation,
                key_indicators=key_indicators,
                extracted_details=extracted_details
            )

        except json.JSONDecodeError as e:
            logger.warning(f"LLM output could not be decoded as JSON: {response_text[:200]}..., error: {e}")
            # Try to extract classification from text if JSON parsing fails
            response_lower = response_text.lower()
            if "cease" in response_lower and ("stop" in response_lower or "desist" in response_lower):
                classification = "Cease"
                confidence = 0.8
                explanation = "Classification extracted from text: contains cease language"
            elif "irrelevant" in response_lower:
                classification = "Irrelevant"
                confidence = 0.7
                explanation = "Classification extracted from text: marked as irrelevant"
            else:
                classification = "Uncertain"
                confidence = 0.5
                explanation = "Could not parse LLM response, defaulting to uncertain"

            return ClassificationResult(
                document_name=document_name,
                date_received=date_received,
                classification=classification,
                confidence=confidence,
                explanation=explanation,
                key_indicators=["Classification extracted from text"],
                extracted_details=ExtractedDetails()
            )
        except Exception as e:
            logger.error(f"Error in LLM-based classification: {e}")
            raise


    def classify_document(
        self,
        document_name: str,
        document_content: str,
        file_path: Optional[str] = None
    ) -> ClassificationResult:
        """
        Classify a document based on its content
        
        Args:
            document_name: Name of the document
            document_content: Extracted text content from the document
            file_path: Optional path to the document file to extract modification time
        
        Returns:
            ClassificationResult with classification, explanation, and extracted details
        """
        try:
            # Get date_received from file modification time or current time
            if file_path and os.path.exists(file_path):
                file_mtime = os.path.getmtime(file_path)
                date_received = datetime.fromtimestamp(file_mtime)
                logger.info(f"Using file modification time for '{document_name}': {date_received.isoformat()}")
            else:
                date_received = datetime.now()
                if file_path:
                    logger.warning(f"File path provided but not found: {file_path}, using current time")
            
            result = self.classify_with_llm(document_name, document_content, date_received)

            self.audit_trail.log_action(
                agent_name=self.name,
                action="Document Classification",
                document_name=document_name,
                classification=result.classification,
                explanation=result.explanation,
                status="success"
            )

            logger.info(
                f"Classified '{document_name}' as {result.classification} "
                f"(confidence: {result.confidence:.2%}) - "
                f"Received: {date_received.isoformat()}"
            )

            return result

        except Exception as e:
            logger.error(f"Error classifying document {document_name}: {e}")
            self.audit_trail.log_action(
                agent_name=self.name,
                action="Document Classification",
                document_name=document_name,
                status="failed",
                explanation=str(e)
            )
            raise