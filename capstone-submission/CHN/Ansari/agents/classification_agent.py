"""
Classification Agent - Classifies documents into CEASE, UNCERTAIN, or IRRELEVANT.
Uses LLM to determine the nature of each document.
"""
import logging
from typing import Optional

from services.llm_service import get_llm_instance, LLMError
from models.schemas import ClassificationResult
from utils.logger import log_audit

logger = logging.getLogger(__name__)

# Classification prompt template
CLASSIFICATION_PROMPT_TEMPLATE = """You are an expert legal document classifier. Your task is to classify a document as one of three categories:

1. "CEASE" - A valid cease and desist letter or demand for action
2. "UNCERTAIN" - An ambiguous document that could be a cease and desist but has unclear intent or requires human review
3. "IRRELEVANT" - A document that is not a cease and desist letter

Analyze the following document text and provide your classification with reasoning.

IMPORTANT: You MUST respond with valid JSON only, no additional text:
{{
    "classification": "CEASE" or "UNCERTAIN" or "IRRELEVANT",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation of your decision"
}}

Document text:
{document_text}
"""


class ClassificationAgent:
    """
    Agent responsible for document classification.
    
    Uses LLM to classify documents into CEASE, UNCERTAIN, or IRRELEVANT categories.
    """
    
    def __init__(self):
        """Initialize the classification agent."""
        self.name = "ClassificationAgent"
        self.llm = get_llm_instance()
        logger.info(f"Initialized {self.name}")
    
    def classify(
        self,
        document_name: str,
        document_text: str,
        confidence_threshold: Optional[float] = None,
    ) -> ClassificationResult:
        """
        Classify a document.
        
        Args:
            document_name: Name of the document
            document_text: Extracted text from document
            confidence_threshold: Optional minimum confidence threshold
            
        Returns:
            ClassificationResult with classification, confidence, and reasoning
            
        Raises:
            LLMError: If LLM call fails
        """
        logger.info(f"[{self.name}] Classifying document: {document_name}")
        
        try:
            # Prepare prompt
            system_prompt = "You are a legal document classification expert."
            user_message = CLASSIFICATION_PROMPT_TEMPLATE.format(document_text=document_text)
            
            # Call LLM
            logger.debug(f"Calling LLM for classification...")
            response = self.llm.call_json(system_prompt, user_message)
            
            # Parse response
            classification = response.get("classification", "UNCERTAIN")
            confidence = float(response.get("confidence", 0.5))
            reasoning = response.get("reasoning", "No reasoning provided")
            
            # Validate classification
            valid_classifications = ["CEASE", "UNCERTAIN", "IRRELEVANT"]
            if classification not in valid_classifications:
                logger.warning(f"Invalid classification returned: {classification}, defaulting to UNCERTAIN")
                classification = "UNCERTAIN"
            
            # Clamp confidence between 0 and 1
            confidence = max(0.0, min(1.0, confidence))
            
            result = ClassificationResult(
                classification=classification,
                confidence=confidence,
                reasoning=reasoning
            )
            
            # Log audit
            log_audit(
                document_name=document_name,
                event_type="classification",
                agent=self.name,
                status="success",
                details={
                    "classification": classification,
                    "confidence": confidence,
                }
            )
            
            logger.info(
                f"[{self.name}] {document_name} classified as {classification} "
                f"(confidence: {confidence:.2f})"
            )
            
            return result
        
        except LLMError as e:
            logger.error(f"[{self.name}] LLM error during classification: {str(e)}")
            log_audit(
                document_name=document_name,
                event_type="classification",
                agent=self.name,
                status="failure",
                details={"error": str(e)},
                error_message=str(e)
            )
            raise
        
        except (KeyError, ValueError, TypeError) as e:
            error_msg = f"Failed to parse classification response: {str(e)}"
            logger.error(f"[{self.name}] {error_msg}")
            log_audit(
                document_name=document_name,
                event_type="classification",
                agent=self.name,
                status="failure",
                details={"error": error_msg},
                error_message=error_msg
            )
            raise LLMError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Unexpected error during classification: {str(e)}"
            logger.error(f"[{self.name}] {error_msg}")
            log_audit(
                document_name=document_name,
                event_type="classification",
                agent=self.name,
                status="failure",
                details={"error": error_msg},
                error_message=error_msg
            )
            raise LLMError(error_msg) from e
