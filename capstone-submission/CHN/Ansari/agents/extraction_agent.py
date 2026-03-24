"""
Extraction Agent - Extracts structured information from CEASE documents.
Pulls sender details, dates, claims, and other relevant information.
"""
import logging
from typing import Optional

from services.llm_service import get_llm_instance, LLMError
from models.schemas import ExtractionResult
from utils.logger import log_audit

logger = logging.getLogger(__name__)

# Extraction prompt template
EXTRACTION_PROMPT_TEMPLATE = """You are an expert legal document analyst. Extract all relevant information from the following cease and desist letter.

Extract the following fields if available:
- sender_name: Name of the person/organization sending the letter
- sender_address: Complete mailing address
- sender_email: Email address if provided
- sender_phone: Phone number if provided
- request_date: Date the letter was sent
- intent_summary: Brief summary of what they're asking you to stop doing
- key_claims: List of legal claims or allegations made
- requested_actions: List of specific actions they want you to take
- deadline: Deadline for compliance if specified
- legal_references: Any laws or legal statutes referenced

Respond with valid JSON only:
{{
    "sender_name": "...",
    "sender_address": "...",
    "sender_email": "...",
    "sender_phone": "...",
    "request_date": "...",
    "intent_summary": "...",
    "key_claims": ["claim1", "claim2"],
    "requested_actions": ["action1", "action2"],
    "deadline": "...",
    "legal_references": ["ref1", "ref2"]
}}

Document text:
{document_text}
"""


class ExtractionAgent:
    """
    Agent responsible for extracting structured information from CEASE documents.
    
    Uses LLM to pull sender details, claims, and requested actions.
    """
    
    def __init__(self):
        """Initialize the extraction agent."""
        self.name = "ExtractionAgent"
        self.llm = get_llm_instance()
        logger.info(f"Initialized {self.name}")
    
    def extract(
        self,
        document_name: str,
        document_text: str,
    ) -> ExtractionResult:
        """
        Extract structured information from a CEASE document.
        
        Args:
            document_name: Name of the document
            document_text: Extracted text from document
            
        Returns:
            ExtractionResult with extracted fields
            
        Raises:
            LLMError: If LLM call fails
        """
        logger.info(f"[{self.name}] Extracting information from: {document_name}")
        
        try:
            # Prepare prompt
            system_prompt = "You are an expert legal document analyst specializing in cease and desist letters."
            user_message = EXTRACTION_PROMPT_TEMPLATE.format(document_text=document_text)
            
            # Call LLM
            logger.debug(f"Calling LLM for extraction...")
            response = self.llm.call_json(system_prompt, user_message)
            
            # Build extraction result with defaults
            extraction_data = {
                "sender_name": response.get("sender_name"),
                "sender_address": response.get("sender_address"),
                "sender_email": response.get("sender_email"),
                "sender_phone": response.get("sender_phone"),
                "request_date": response.get("request_date"),
                "intent_summary": response.get("intent_summary", "Unable to determine intent"),
                "key_claims": response.get("key_claims", []),
                "requested_actions": response.get("requested_actions", []),
                "deadline": response.get("deadline"),
                "legal_references": response.get("legal_references", []),
            }
            
            result = ExtractionResult(**extraction_data)
            
            # Log audit
            log_audit(
                document_name=document_name,
                event_type="extraction",
                agent=self.name,
                status="success",
                details={
                    "sender_name": result.sender_name or "Not found",
                    "claims_count": len(result.key_claims),
                    "actions_count": len(result.requested_actions),
                }
            )
            
            logger.info(
                f"[{self.name}] Successfully extracted data from {document_name}: "
                f"{len(result.key_claims)} claims, {len(result.requested_actions)} actions"
            )
            
            return result
        
        except LLMError as e:
            logger.error(f"[{self.name}] LLM error during extraction: {str(e)}")
            log_audit(
                document_name=document_name,
                event_type="extraction",
                agent=self.name,
                status="failure",
                details={"error": str(e)},
                error_message=str(e)
            )
            raise
        
        except (KeyError, ValueError, TypeError) as e:
            error_msg = f"Failed to parse extraction response: {str(e)}"
            logger.error(f"[{self.name}] {error_msg}")
            log_audit(
                document_name=document_name,
                event_type="extraction",
                agent=self.name,
                status="failure",
                details={"error": error_msg},
                error_message=error_msg
            )
            raise LLMError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Unexpected error during extraction: {str(e)}"
            logger.error(f"[{self.name}] {error_msg}")
            log_audit(
                document_name=document_name,
                event_type="extraction",
                agent=self.name,
                status="failure",
                details={"error": error_msg},
                error_message=error_msg
            )
            raise LLMError(error_msg) from e
