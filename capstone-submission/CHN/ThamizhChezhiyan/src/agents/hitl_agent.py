"""
Human-In-The-Loop (HITL) Agent - Manages manual review workflow
"""
import json
from datetime import datetime
from pathlib import Path
from src.config.config import LOGS_DIR
from src.tools.audit_logger import get_audit_trail
import logging
import time

logger = logging.getLogger(__name__)


class HITLAgent:
    """Agent for managing human-in-the-loop review process"""

    def __init__(self):
        """Initialize the HITL agent"""
        self.audit_trail = get_audit_trail()
        self.name = "HITLAgent"
        self.review_queue_file = LOGS_DIR / "review_queue.json"
        self.review_decisions_file = LOGS_DIR / "review_decisions.json"
        self._init_queue_file()

    def _init_queue_file(self) -> None:
        """Initialize review queue file if it doesn't exist"""
        if not self.review_queue_file.exists():
            try:
                # Ensure parent directory exists
                self.review_queue_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.review_queue_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                logger.info(f"Review queue file initialized: {self.review_queue_file}")
            except Exception as e:
                logger.error(f"Error initializing review queue file: {e}")

    def queue_for_review(
        self,
        document_name: str,
        document_content: str,
        classification: str,
        confidence: float,
        explanation: str,
        key_indicators: list,
        max_retries: int = 3
    ) -> bool:
        """
        Queue a document for human review with retry logic
        
        Args:
            document_name: Name of the document
            document_content: Content of the document
            classification: Current classification
            confidence: Confidence score
            explanation: Explanation for classification
            key_indicators: Key indicators found
            max_retries: Maximum number of retry attempts
        
        Returns:
            True if queued successfully, False otherwise
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                # Create preview - limit to 500 chars to avoid JSON serialization issues
                preview = document_content[:500] if document_content else ""
                
                review_item = {
                    "id": f"{document_name}_{datetime.utcnow().isoformat()}",
                    "document_name": document_name,
                    "document_content_preview": preview,  # Store only preview
                    "classification": classification,
                    "confidence": confidence,
                    "explanation": explanation,
                    "key_indicators": key_indicators,
                    "queued_at": datetime.utcnow().isoformat(),
                    "status": "pending_review"
                }

                # Ensure review queue file exists
                if not self.review_queue_file.exists():
                    self.review_queue_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(self.review_queue_file, 'w', encoding='utf-8') as f:
                        json.dump([], f)

                # Add to review queue with proper encoding
                with open(self.review_queue_file, 'r', encoding='utf-8') as f:
                    queue = json.load(f)

                queue.append(review_item)

                # Write with ensure_ascii=False to handle unicode properly
                with open(self.review_queue_file, 'w', encoding='utf-8') as f:
                    json.dump(queue, f, indent=2, ensure_ascii=False)

                # Log the action
                self.audit_trail.log_action(
                    agent_name=self.name,
                    action="Queue for Review",
                    document_name=document_name,
                    classification=classification,
                    explanation=f"Document queued for human review. Confidence: {confidence}",
                    status="review_required"
                )

                logger.info(f"Document queued for review: {document_name}")
                return True

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1}/{max_retries} - Error queuing document for review: {last_error}")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt)  # Exponential backoff: 1, 2, 4 seconds
                    time.sleep(wait_time)
                continue
        
        # All retries exhausted
        logger.error(f"Failed to queue document {document_name} after {max_retries} attempts: {last_error}")
        self.audit_trail.log_action(
            agent_name=self.name,
            action="Queue for Review",
            document_name=document_name,
            status="failed",
            explanation=f"Queueing error (retries exhausted): {last_error}"
        )
        return False

    def get_review_queue(self, status: str = "pending_review") -> list:
        """
        Get documents in review queue
        
        Args:
            status: Filter by status (default: pending_review)
        
        Returns:
            List of documents pending review
        """
        try:
            with open(self.review_queue_file, 'r', encoding='utf-8') as f:
                queue = json.load(f)

            if status:
                queue = [item for item in queue if item.get("status") == status]

            self.audit_trail.log_action(
                agent_name=self.name,
                action="Get Review Queue",
                explanation=f"Retrieved {len(queue)} items from review queue",
                status="success"
            )

            return queue

        except Exception as e:
            logger.error(f"Error retrieving review queue: {e}")
            return []

    def submit_review_decision(
        self,
        document_name: str,
        human_decision: str,
        reviewer_notes: str = "",
        database_agent=None,
        archiving_agent=None
    ) -> bool:
        """
        Submit a human review decision
        
        Args:
            document_name: Name of the document
            human_decision: Human's decision (Cease or Irrelevant)
            reviewer_notes: Additional notes from reviewer
            database_agent: Database agent for storing cease requests (injected by manager)
            archiving_agent: Archiving agent for archiving irrelevant documents (injected by manager)
        
        Returns:
            True if decision recorded successfully, False otherwise
        """
        try:
            decision = {
                "document_name": document_name,
                "human_decision": human_decision,
                "reviewer_notes": reviewer_notes,
                "decision_timestamp": datetime.utcnow().isoformat()
            }

            # Add to decisions file
            decisions = []
            if self.review_decisions_file.exists():
                with open(self.review_decisions_file, 'r', encoding='utf-8') as f:
                    decisions = json.load(f)

            decisions.append(decision)

            with open(self.review_decisions_file, 'w', encoding='utf-8') as f:
                json.dump(decisions, f, indent=2, ensure_ascii=False)

            # Remove from review queue
            with open(self.review_queue_file, 'r', encoding='utf-8') as f:
                queue = json.load(f)

            # Get the document details from queue for archiving
            queue_doc = None
            for item in queue:
                if item.get("document_name") == document_name:
                    queue_doc = item
                    break

            queue = [item for item in queue if item.get("document_name") != document_name]

            with open(self.review_queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue, f, indent=2, ensure_ascii=False)

            # Process decision based on human choice
            if human_decision == "Cease" and database_agent:
                # Store in database for Cease decisions
                success = database_agent.store_cease_request(
                    document_name=document_name,
                    classification="Cease",
                    extracted_details=f"Human reviewed: {reviewer_notes}",
                    document_content_preview=queue_doc.get("document_content_preview", "") if queue_doc else "",
                    processing_status="human_reviewed"
                )
                if not success:
                    logger.warning(f"Failed to store cease request in database for {document_name}")
                    
            elif human_decision == "Irrelevant" and archiving_agent:
                # Archive for Irrelevant decisions
                success = archiving_agent.archive_document(
                    document_name=document_name,
                    document_path=queue_doc.get("document_path") if queue_doc else None
                )
                if not success:
                    logger.warning(f"Failed to archive irrelevant document {document_name}")

            # Log the action
            self.audit_trail.log_action(
                agent_name=self.name,
                action="Submit Review Decision",
                document_name=document_name,
                classification=human_decision,
                explanation=f"Human review decision: {human_decision}. Notes: {reviewer_notes}",
                status="success"
            )

            logger.info(f"Review decision submitted for {document_name}: {human_decision}")
            return True

        except Exception as e:
            logger.error(f"Error submitting review decision: {e}")
            self.audit_trail.log_action(
                agent_name=self.name,
                action="Submit Review Decision",
                document_name=document_name,
                status="failed"
            )
            return False

    def get_review_decisions(self, document_name: str = None) -> list:
        """
        Retrieve review decisions
        
        Args:
            document_name: Optional filter by document name
        
        Returns:
            List of review decisions
        """
        try:
            if not self.review_decisions_file.exists():
                return []

            with open(self.review_decisions_file, 'r') as f:
                decisions = json.load(f)

            if document_name:
                decisions = [d for d in decisions if d.get("document_name") == document_name]

            self.audit_trail.log_action(
                agent_name=self.name,
                action="Get Review Decisions",
                explanation=f"Retrieved {len(decisions)} decisions",
                status="success"
            )

            return decisions

        except Exception as e:
            logger.error(f"Error retrieving review decisions: {e}")
            return []

    def get_hitl_stats(self) -> dict:
        """
        Get statistics about HITL process
        
        Returns:
            Dictionary with HITL statistics
        """
        try:
            pending = self.get_review_queue(status="pending_review")
            decisions = self.get_review_decisions()

            # Count cease and irrelevant decisions
            cease_decisions = len([d for d in decisions if d.get("human_decision") == "Cease"])
            irrelevant_decisions = len([d for d in decisions if d.get("human_decision") == "Irrelevant"])

            stats = {
                "pending_review": len(pending),
                "total_decisions": len(decisions),
                "cease_decisions": cease_decisions,
                "irrelevant_decisions": irrelevant_decisions,
                "review_queue_file": str(self.review_queue_file),
                "decisions_file": str(self.review_decisions_file)
            }

            self.audit_trail.log_action(
                agent_name=self.name,
                action="Get HITL Statistics",
                explanation=f"HITL stats: {stats}",
                status="success"
            )

            return stats

        except Exception as e:
            logger.error(f"Error getting HITL statistics: {e}")
            return {"error": str(e)}
