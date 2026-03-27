"""
Manager/Orchestrator Agent - Coordinates all agents using LangGraph
"""
from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from src.config.config import GROQ_API_KEY, MODEL_NAME
from src.agents.classification_agent import ClassificationAgent
from src.agents.database_agent import DatabaseAgent
from src.agents.archiving_agent import ArchivingAgent
from src.agents.audit_agent import AuditAgent
from src.agents.hitl_agent import HITLAgent
from src.tools.document_loader import extract_text
from src.tools.audit_logger import get_audit_trail
import logging

logger = logging.getLogger(__name__)


class DocumentProcessingState(TypedDict):
    """State for document processing workflow"""
    document_name: str
    document_path: str
    document_content: str
    classification: str
    confidence: float
    explanation: str
    key_indicators: list
    extraction_error: bool
    processing_complete: bool
    processing_status: str


class ManagerAgent:
    """Manager agent that orchestrates the multi-agent system using LangGraph"""

    def __init__(self):
        """Initialize the manager agent with all sub-agents"""
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required for classification")

        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=MODEL_NAME,
            temperature=0.0,
            streaming=False
        )

        self.classification_agent = ClassificationAgent(self.llm)
        self.database_agent = DatabaseAgent()
        self.archiving_agent = ArchivingAgent()
        self.audit_agent = AuditAgent()
        self.hitl_agent = HITLAgent()
        self.audit_trail = get_audit_trail()
        self.name = "ManagerAgent"

        # Initialize LangGraph workflow
        self.workflow = self._create_workflow()
        self.graph = self.workflow.compile()

    def _create_workflow(self) -> StateGraph:
        """
        Create the LangGraph workflow for document processing
        
        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(DocumentProcessingState)

        # Define nodes
        workflow.add_node("extract_text", self._extract_text_node)
        workflow.add_node("classify", self._classify_node)
        workflow.add_node("route_decision", self._route_decision_node)
        workflow.add_node("store_cease", self._store_cease_node)
        workflow.add_node("archive_irrelevant", self._archive_irrelevant_node)
        workflow.add_node("queue_for_review", self._queue_for_review_node)
        workflow.add_node("complete", self._complete_node)

        # Define edges
        workflow.set_entry_point("extract_text")
        workflow.add_edge("extract_text", "classify")
        workflow.add_edge("classify", "route_decision")

        # Conditional routing
        workflow.add_conditional_edges(
            "route_decision",
            self._route_based_classification,
            {
                "cease": "store_cease",
                "irrelevant": "archive_irrelevant",
                "uncertain": "queue_for_review"
            }
        )

        # All paths lead to complete
        workflow.add_edge("store_cease", "complete")
        workflow.add_edge("archive_irrelevant", "complete")
        workflow.add_edge("queue_for_review", "complete")
        workflow.add_edge("complete", END)

        return workflow

    def _extract_text_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Node: Extract text from document"""
        try:
            logger.info(f"Extracting text from {state['document_name']}")
            
            content = extract_text(state['document_path'])
            
            if not content:
                state['extraction_error'] = True
                logger.warning(f"Failed to extract text from {state['document_name']}")
                self.audit_trail.log_action(
                    agent_name=self.name,
                    action="Extract Text",
                    document_name=state['document_name'],
                    status="failed"
                )
            else:
                state['document_content'] = content
                state['extraction_error'] = False
                self.audit_trail.log_action(
                    agent_name=self.name,
                    action="Extract Text",
                    document_name=state['document_name'],
                    explanation=f"Extracted {len(content)} characters",
                    status="success"
                )
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            state['extraction_error'] = True

        return state

    def _classify_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Node: Classify document"""
        try:
            if state.get('extraction_error'):
                logger.warning(f"Skipping classification due to extraction error")
                state['classification'] = "Uncertain"
                state['confidence'] = 0.0
                state['explanation'] = "Could not extract text from document"
                state['key_indicators'] = []
                return state

            logger.info(f"Classifying {state['document_name']}")
            
            result = self.classification_agent.classify_document(
                state['document_name'],
                state['document_content'],
                file_path=state['document_path']
            )

            state['classification'] = result.classification
            state['confidence'] = result.confidence
            state['explanation'] = result.explanation
            state['key_indicators'] = result.key_indicators

        except Exception as e:
            logger.error(f"Error classifying document: {e}")
            state['classification'] = "Uncertain"
            state['confidence'] = 0.0
            state['explanation'] = f"Classification error: {str(e)}"

        return state

    def _route_decision_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Node: Prepare for routing decision"""
        logger.info(f"Routing decision for {state['document_name']}: {state['classification']}")
        return state

    def _route_based_classification(self, state: DocumentProcessingState) -> str:
        """Conditional edge: Route based on classification"""
        classification = state.get('classification', 'Uncertain')
        
        if classification == "Cease":
            return "cease"
        elif classification == "Irrelevant":
            return "irrelevant"
        else:
            return "uncertain"

    def _store_cease_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Node: Store cease request in database"""
        try:
            logger.info(f"Storing cease request: {state['document_name']}")
            
            # Extract relevant information from content
            extracted_details = self._extract_details(state['document_content'])

            success = self.database_agent.store_cease_request(
                document_name=state['document_name'],
                classification=state['classification'],
                extracted_details=extracted_details,
                document_content_preview=state['document_content'][:300],
                processing_status="processed"
            )

            state['processing_status'] = "stored_in_database" if success else "storage_failed"
            state['processing_complete'] = success

        except Exception as e:
            logger.error(f"Error storing cease request: {e}")
            state['processing_status'] = "storage_failed"
            state['processing_complete'] = False

        return state

    def _archive_irrelevant_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Node: Archive irrelevant document"""
        try:
            logger.info(f"Archiving irrelevant document: {state['document_name']}")
            
            success = self.archiving_agent.archive_document(
                state['document_name'],
                state['document_path']
            )

            state['processing_status'] = "archived" if success else "archive_failed"
            state['processing_complete'] = success

        except Exception as e:
            logger.error(f"Error archiving document: {e}")
            state['processing_status'] = "archive_failed"
            state['processing_complete'] = False

        # Memory cleanup: free large fields
        state['document_content'] = None
        state['document_path'] = None
        state['key_indicators'] = []
        state['explanation'] = ''
        return state

    def _queue_for_review_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Node: Queue uncertain document for human review"""
        try:
            logger.info(f"Queuing for review: {state['document_name']}")
            
            success = self.hitl_agent.queue_for_review(
                document_name=state['document_name'],
                document_content=state['document_content'],
                classification=state['classification'],
                confidence=state['confidence'],
                explanation=state['explanation'],
                key_indicators=state['key_indicators']
            )

            state['processing_status'] = "queued_for_review" if success else "queue_failed"
            state['processing_complete'] = success

        except Exception as e:
            logger.error(f"Error queuing for review: {e}")
            state['processing_status'] = "queue_failed"
            state['processing_complete'] = False

        return state

    def _complete_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Node: Complete processing"""
        logger.info(
            f"Processing complete for {state['document_name']}: "
            f"{state['processing_status']}"
        )
        # Memory cleanup: free large fields
        state['document_content'] = None
        state['document_path'] = None
        state['key_indicators'] = []
        state['explanation'] = ''
        return state

    def process_document(self, document_path: str, document_name: str) -> Dict[str, Any]:
        """
        Process a single document through the workflow
        
        Args:
            document_path: Path to the document
            document_name: Name of the document
        
        Returns:
            Processing result
        """
        try:
            initial_state: DocumentProcessingState = {
                'document_name': document_name,
                'document_path': document_path,
                'document_content': '',
                'classification': 'Uncertain',
                'confidence': 0.0,
                'explanation': '',
                'key_indicators': [],
                'extraction_error': False,
                'processing_complete': False,
                'processing_status': 'initiated'
            }

            # Run the workflow
            final_state = self.graph.invoke(initial_state)

            # Log processing completion
            self.audit_trail.log_action(
                agent_name=self.name,
                action="Process Document",
                document_name=document_name,
                classification=final_state['classification'],
                explanation=f"Status: {final_state['processing_status']}",
                status="success" if final_state['processing_complete'] else "failed"
            )

            return final_state

        except Exception as e:
            logger.error(f"Error processing document {document_name}: {e}")
            self.audit_trail.log_action(
                agent_name=self.name,
                action="Process Document",
                document_name=document_name,
                status="failed"
            )
            raise

    def process_batch(self, documents: list) -> list:
        """
        Process multiple documents
        
        Args:
            documents: List of (document_path, document_name) tuples
        
        Returns:
            List of processing results
        """
        results = []
        logger.info(f"Starting batch processing of {len(documents)} documents")

        for doc_path, doc_name in documents:
            try:
                result = self.process_document(doc_path, doc_name)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing {doc_name}: {e}")
                results.append({
                    'document_name': doc_name,
                    'processing_status': 'error',
                    'processing_complete': False,
                    'error': str(e)
                })

        logger.info(f"Batch processing complete: {len(results)} documents processed")
        return results

    def _extract_details(self, content: str) -> str:
        """
        Extract key details from document content
        
        Args:
            content: Document content
        
        Returns:
            Extracted details as string
        """
        # Simple extraction - in production, use NLP
        lines = content.split('\n')
        relevant_lines = [line for line in lines if line.strip() and len(line.split()) > 3]
        return '\n'.join(relevant_lines[:5])  # First 5 significant lines

    def get_system_status(self) -> dict:
        """
        Get overall system status and statistics
        
        Returns:
            Dictionary with system statistics
        """
        try:
            db_stats = self.database_agent.get_document_stats()
            archive_stats = self.archiving_agent.get_archive_stats()
            hitl_stats = self.hitl_agent.get_hitl_stats()
            audit_report = self.audit_agent.generate_audit_report()

            # Calculate total documents processed from all sources
            cease_count = db_stats.get("total_documents", 0)
            archived_count = archive_stats.get("total_archived", 0)
            uncertain_pending = hitl_stats.get("pending_review", 0)
            # decided documents in human review should be already stored as Cease or Archived
            total_documents_processed = cease_count + archived_count + uncertain_pending

            # Handle audit report errors
            if "error" in audit_report:
                logger.warning(f"Audit report error: {audit_report['error']}")
                audit_summary = {"error": audit_report["error"]}
            else:
                audit_summary = {
                    "total_entries": audit_report.get("total_audit_entries", 0),
                    "agent_actions": audit_report.get("agent_actions", {}),
                    "status_summary": audit_report.get("status_summary", {})
                }

            status = {
                "system_status": "operational",
                "database_stats": {**db_stats, "total_documents": total_documents_processed},
                "archive_stats": archive_stats,
                "hitl_stats": hitl_stats,
                "audit_summary": audit_summary
            }

            return status

        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"system_status": "error", "error": str(e)}
