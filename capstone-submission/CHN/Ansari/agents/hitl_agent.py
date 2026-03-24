"""
HITL Agent - Human-In-The-Loop review system.
Handles manual review and decision-making for uncertain documents.
"""
import logging
from datetime import datetime
from typing import Literal

from models.schemas import HITLRequest, HITLResponse
from utils.logger import log_audit

logger = logging.getLogger(__name__)


class HITLAgent:
    """
    Agent for Human-In-The-Loop (HITL) document review.
    
    Allows human operators to review and reclassify uncertain documents.
    """
    
    def __init__(self):
        """Initialize the HITL agent."""
        self.name = "HITLAgent"
        logger.info(f"Initialized {self.name}")
    
    def request_human_review(
        self,
        document_name: str,
        extracted_text: str,
        initial_classification: str,
        confidence: float,
        reasoning: str,
    ) -> HITLRequest:
        """
        Create a human review request.
        
        Args:
            document_name: Name of the document
            extracted_text: Extracted text from document
            initial_classification: Initial classification result
            confidence: Classification confidence
            reasoning: Classification reasoning
            
        Returns:
            HITLRequest object
        """
        logger.info(f"[{self.name}] Creating review request for: {document_name}")
        
        request = HITLRequest(
            document_name=document_name,
            extracted_text=extracted_text,
            initial_classification=initial_classification,
            confidence=confidence,
            reasoning=reasoning,
        )
        
        log_audit(
            document_name=document_name,
            event_type="hitl_request",
            agent=self.name,
            status="pending",
            details={
                "initial_classification": initial_classification,
                "confidence": confidence,
            }
        )
        
        return request
    
    def process_human_decision(
        self,
        document_name: str,
        human_decision: Literal["CEASE", "UNCERTAIN", "IRRELEVANT"],
        human_reasoning: str,
    ) -> HITLResponse:
        """
        Process human decision for a document.
        
        Args:
            document_name: Name of the document
            human_decision: Human's classification decision
            human_reasoning: Human's explanation for the decision
            
        Returns:
            HITLResponse object
        """
        logger.info(f"[{self.name}] Processing human decision for: {document_name}")
        
        # Validate decision
        valid_decisions = ["CEASE", "UNCERTAIN", "IRRELEVANT"]
        if human_decision not in valid_decisions:
            logger.warning(f"Invalid human decision: {human_decision}")
            raise ValueError(f"Invalid decision. Must be one of: {valid_decisions}")
        
        response = HITLResponse(
            human_decision=human_decision,
            human_reasoning=human_reasoning,
            decision_timestamp=datetime.now(),
        )
        
        log_audit(
            document_name=document_name,
            event_type="hitl_decision",
            agent=self.name,
            status="success",
            details={
                "human_decision": human_decision,
            }
        )
        
        logger.info(f"[{self.name}] Human decision recorded: {human_decision}")
        
        return response
    
    def cli_review_interface(self, hitl_request: HITLRequest) -> HITLResponse:
        """
        Interactive CLI-based human review interface.
        
        Args:
            hitl_request: Review request object
            
        Returns:
            HITLResponse with human decision
        """
        logger.info(f"[{self.name}] Starting CLI review interface")
        
        print("\n" + "="*80)
        print("HUMAN-IN-THE-LOOP REVIEW - UNCERTAIN DOCUMENT")
        print("="*80)
        print(f"\nDocument: {hitl_request.document_name}")
        print(f"Initial Classification: {hitl_request.initial_classification}")
        print(f"Confidence: {hitl_request.confidence:.2%}")
        print(f"Reasoning: {hitl_request.reasoning}")
        print("\n" + "-"*80)
        print("DOCUMENT PREVIEW:")
        print("-"*80)
        
        # Show text preview
        text_preview = hitl_request.extracted_text[:1000]
        print(text_preview)
        if len(hitl_request.extracted_text) > 1000:
            print(f"\n... (text truncated - total {len(hitl_request.extracted_text)} chars)")
        
        print("\n" + "-"*80)
        print("YOUR DECISION:")
        print("-"*80)
        print("Enter your classification decision:")
        print("  1. CEASE - Valid cease and desist letter")
        print("  2. IRRELEVANT - Not a cease and desist")
        print("  3. UNCERTAIN - Still uncertain, needs further review")
        print("  4. SKIP - Skip this document")
        print()
        
        # Loop until valid response
        while True:
            try:
                choice = input("Enter your choice (1-4): ").strip()
                
                if choice == "1":
                    decision = "CEASE"
                    break
                elif choice == "2":
                    decision = "IRRELEVANT"
                    break
                elif choice == "3":
                    decision = "UNCERTAIN"
                    break
                elif choice == "4":
                    logger.info(f"[{self.name}] User skipped review for {hitl_request.document_name}")
                    return None
                else:
                    print("Invalid choice. Please enter 1, 2, 3, or 4.")
                    continue
            
            except KeyboardInterrupt:
                logger.info(f"[{self.name}] Review interrupted by user")
                print("\nReview cancelled.")
                return None
        
        # Get reasoning
        print(f"\nYou selected: {decision}")
        reasoning = input("Enter your reasoning for this decision: ").strip()
        
        if not reasoning:
            print("Reasoning cannot be empty.")
            return self.cli_review_interface(hitl_request)
        
        # Create response
        return self.process_human_decision(
            document_name=hitl_request.document_name,
            human_decision=decision,
            human_reasoning=reasoning,
        )
