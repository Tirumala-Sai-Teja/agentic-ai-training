"""
LangGraph workflow orchestration.
Defines the multi-agent graph for document processing.
"""
import logging
from typing import Any, Dict, Optional
from datetime import datetime

from langgraph.graph import StateGraph, START, END

from models.schemas import (
    ProcessingState,
    DocumentIngestionInput,
    ClassificationResult,
    ExtractionResult,
    HITLRequest,
    HITLResponse,
)
from agents.ingestion_agent import IngestionAgent
from agents.classification_agent import ClassificationAgent
from agents.extraction_agent import ExtractionAgent
from agents.database_agent import DatabaseAgent
from agents.archival_agent import ArchivalAgent
from agents.hitl_agent import HITLAgent
from agents.audit_agent import AuditAgent

logger = logging.getLogger(__name__)


class DocumentProcessingGraph:
    """
    LangGraph workflow for document processing.
    
    Orchestrates the multi-agent system following this flow:
    START → Ingestion → Classification → 
        if CEASE → Extraction → Database → Audit → END
        if IRRELEVANT → Archive → Audit → END
        if UNCERTAIN → HITL → Archive/Database → Audit → END
    """
    
    def __init__(self):
        """Initialize the document processing graph."""
        self.ingestion_agent = IngestionAgent()
        self.classification_agent = ClassificationAgent()
        self.extraction_agent = ExtractionAgent()
        self.database_agent = DatabaseAgent()
        self.archival_agent = ArchivalAgent()
        self.hitl_agent = HITLAgent()
        self.audit_agent = AuditAgent()
        
        self.graph = self._build_graph()
        logger.info("Initialized DocumentProcessingGraph")
    
    def _build_graph(self) -> Any:
        """
        Build the LangGraph workflow.
        
        Returns:
            Compiled graph instance
        """
        graph_builder = StateGraph(ProcessingState)
        
        # Add nodes
        graph_builder.add_node("ingestion", self._ingestion_node)
        graph_builder.add_node("classification", self._classification_node)
        graph_builder.add_node("extraction", self._extraction_node)
        graph_builder.add_node("database", self._database_node)
        graph_builder.add_node("archive", self._archive_node)
        graph_builder.add_node("hitl", self._hitl_node)
        graph_builder.add_node("audit", self._audit_node)
        
        # Add edges
        graph_builder.add_edge(START, "ingestion")
        graph_builder.add_edge("ingestion", "classification")
        
        # Conditional routing based on classification
        graph_builder.add_conditional_edges(
            "classification",
            self._route_classification,
            {
                "cease_path": "extraction",
                "irrelevant_path": "archive",
                "uncertain_path": "hitl",
                "error_path": "audit",
            }
        )
        
        # CEASE path
        graph_builder.add_edge("extraction", "database")
        graph_builder.add_edge("database", "audit")
        
        # IRRELEVANT path
        graph_builder.add_edge("archive", "audit")
        
        # UNCERTAIN path
        graph_builder.add_edge("hitl", "database")
        
        # Final audit node
        graph_builder.add_edge("audit", END)
        
        return graph_builder.compile()
    
    def _route_classification(self, state: ProcessingState) -> str:
        """
        Route based on classification result.
        
        Args:
            state: Current processing state
            
        Returns:
            Route name (cease_path, irrelevant_path, uncertain_path, error_path)
        """
        if state.error_message:
            return "error_path"
        
        if not state.classification_result:
            state.error_message = "No classification result"
            return "error_path"
        
        classification = state.classification_result.classification
        
        if classification == "CEASE":
            return "cease_path"
        elif classification == "IRRELEVANT":
            return "irrelevant_path"
        elif classification == "UNCERTAIN":
            return "uncertain_path"
        else:
            state.error_message = f"Unknown classification: {classification}"
            return "error_path"
    
    def _ingestion_node(self, state: ProcessingState) -> ProcessingState:
        """
        Ingestion node - Extract text from PDF.
        
        Args:
            state: Current processing state
            
        Returns:
            Updated processing state
        """
        logger.info(f"Entering ingestion node for {state.document_name}")
        
        try:
            input_data = DocumentIngestionInput(
                document_path=state.document_path,
                document_name=state.document_name,
            )
            
            output = self.ingestion_agent.process(input_data)
            state.extracted_text = output.extracted_text
            state.processing_status = "processing"
            
            logger.info(f"Ingestion completed for {state.document_name}")
            
        except Exception as e:
            state.error_message = f"Ingestion failed: {str(e)}"
            state.processing_status = "failed"
            logger.error(f"Ingestion error: {state.error_message}")
        
        return state
    
    def _classification_node(self, state: ProcessingState) -> ProcessingState:
        """
        Classification node - Classify document.
        
        Args:
            state: Current processing state
            
        Returns:
            Updated processing state
        """
        logger.info(f"Entering classification node for {state.document_name}")
        
        try:
            if not state.extracted_text:
                raise ValueError("No extracted text available for classification")
            
            result = self.classification_agent.classify(
                state.document_name,
                state.extracted_text,
            )
            
            state.classification_result = result
            logger.info(f"Classification completed: {result.classification} ({result.confidence:.2%})")
            
        except Exception as e:
            state.error_message = f"Classification failed: {str(e)}"
            state.processing_status = "failed"
            logger.error(f"Classification error: {state.error_message}")
        
        return state
    
    def _extraction_node(self, state: ProcessingState) -> ProcessingState:
        """
        Extraction node - Extract structured data from CEASE document.
        
        Args:
            state: Current processing state
            
        Returns:
            Updated processing state
        """
        logger.info(f"Entering extraction node for {state.document_name}")
        
        try:
            if not state.extracted_text:
                raise ValueError("No extracted text available for extraction")
            
            result = self.extraction_agent.extract(
                state.document_name,
                state.extracted_text,
            )
            
            state.extraction_result = result
            logger.info(f"Extraction completed for {state.document_name}")
            
        except Exception as e:
            state.error_message = f"Extraction failed: {str(e)}"
            state.processing_status = "failed"
            logger.error(f"Extraction error: {state.error_message}")
        
        return state
    
    def _database_node(self, state: ProcessingState) -> ProcessingState:
        """
        Database node - Store CEASE record.
        
        Args:
            state: Current processing state
            
        Returns:
            Updated processing state
        """
        logger.info(f"Entering database node for {state.document_name}")
        
        try:
            if not state.classification_result:
                raise ValueError("No classification result available")
            
            # Only store CEASE records
            if state.classification_result.classification == "CEASE":
                if not state.extraction_result:
                    raise ValueError("No extraction result available for CEASE document")
                
                record_id = self.database_agent.store_cease_record(
                    document_name=state.document_name,
                    received_date=state.received_date,
                    extraction_result=state.extraction_result,
                    classification=state.classification_result.classification,
                    reasoning=state.classification_result.reasoning,
                    confidence=state.classification_result.confidence,
                    full_text=state.extracted_text,
                )
                
                state.database_record_id = record_id
                logger.info(f"Database stored record {record_id} for {state.document_name}")
            
            # For UNCERTAIN documents that were reclassified as CEASE by human
            elif state.classification_result.classification == "CEASE" and state.human_decision == "CEASE":
                if not state.extraction_result:
                    raise ValueError("No extraction result available for CEASE document")
                
                record_id = self.database_agent.store_cease_record(
                    document_name=state.document_name,
                    received_date=state.received_date,
                    extraction_result=state.extraction_result,
                    classification="CEASE",
                    reasoning=f"Human review: {state.human_decision}",
                    confidence=1.0,
                    full_text=state.extracted_text,
                )
                
                state.database_record_id = record_id
                logger.info(f"Database stored human-reviewed record {record_id}")
            
        except Exception as e:
            state.error_message = f"Database operation failed: {str(e)}"
            state.processing_status = "failed"
            logger.error(f"Database error: {state.error_message}")
        
        return state
    
    def _archive_node(self, state: ProcessingState) -> ProcessingState:
        """
        Archive node - Archive IRRELEVANT documents.
        
        Args:
            state: Current processing state
            
        Returns:
            Updated processing state
        """
        logger.info(f"Entering archive node for {state.document_name}")
        
        try:
            classification = state.classification_result.classification
            
            # Archive IRRELEVANT documents
            if classification == "IRRELEVANT":
                record_id = self.archival_agent.archive_document(
                    document_name=state.document_name,
                    received_date=state.received_date,
                    classification=classification,
                    extracted_text=state.extracted_text,
                )
                state.archive_record_id = record_id
                logger.info(f"Archived IRRELEVANT document with record {record_id}")
            
            elif state.human_decision == "IRRELEVANT":
                record_id = self.archival_agent.archive_document(
                    document_name=state.document_name,
                    received_date=state.received_date,
                    classification="IRRELEVANT",
                    extracted_text=state.extracted_text,
                )
                state.archive_record_id = record_id
                logger.info(f"Archived human-reviewed IRRELEVANT document")
        
        except Exception as e:
            state.error_message = f"Archive operation failed: {str(e)}"
            state.processing_status = "failed"
            logger.error(f"Archive error: {state.error_message}")
        
        return state
    
    def _hitl_node(self, state: ProcessingState) -> ProcessingState:
        """
        HITL node - Human-in-the-loop review.
        
        Args:
            state: Current processing state
            
        Returns:
            Updated processing state
        """
        logger.info(f"Entering HITL node for {state.document_name}")
        state.processing_status = "awaiting_human_review"
        
        try:
            # Create review request
            review_request = self.hitl_agent.request_human_review(
                document_name=state.document_name,
                extracted_text=state.extracted_text,
                initial_classification=state.classification_result.classification,
                confidence=state.classification_result.confidence,
                reasoning=state.classification_result.reasoning,
            )
            
            # Get human decision via CLI
            human_response = self.hitl_agent.cli_review_interface(review_request)
            
            if human_response:
                state.human_decision = human_response.human_decision
                
                # If human decides it's a CEASE, trigger extraction
                if human_response.human_decision == "CEASE":
                    result = self.extraction_agent.extract(
                        state.document_name,
                        state.extracted_text,
                    )
                    state.extraction_result = result
                
                logger.info(f"Human decision recorded: {human_response.human_decision}")
            else:
                logger.info(f"HITL review skipped for {state.document_name}")
        
        except Exception as e:
            state.error_message = f"HITL operation failed: {str(e)}"
            state.processing_status = "failed"
            logger.error(f"HITL error: {state.error_message}")
        
        return state
    
    def _audit_node(self, state: ProcessingState) -> ProcessingState:
        """
        Audit node - Log all operations.
        
        Args:
            state: Current processing state
            
        Returns:
        Updated processing state
        """
        logger.info(f"Entering audit node for {state.document_name}")
        
        try:
            # Log final status
            if state.processing_status != "failed":
                state.processing_status = "completed"
            
            status = "success" if state.processing_status == "completed" else "failure"
            
            self.audit_agent.log_event(
                document_name=state.document_name,
                event_type="workflow_complete",
                agent="DocumentProcessingGraph",
                details={
                    "status": state.processing_status,
                    "classification": state.classification_result.classification if state.classification_result else "N/A",
                    "database_record_id": state.database_record_id,
                    "archive_record_id": state.archive_record_id,
                    "human_decision": state.human_decision,
                },
                status=status,
                error_message=state.error_message,
            )
            
            logger.info(f"Audit logged for {state.document_name}")
            
        except Exception as e:
            logger.error(f"Audit logging error: {str(e)}")
        
        return state
    
    def process_document(
        self,
        document_path: str,
        document_name: str,
    ) -> ProcessingState:
        """
        Process a document through the workflow.
        
        Args:
            document_path: Path to the document
            document_name: Name of the document
            
        Returns:
            Final processing state
        """
        logger.info(f"Starting workflow for document: {document_name}")
        
        # Create initial state
        initial_state = ProcessingState(
            document_name=document_name,
            document_path=document_path,
            extracted_text="",
            received_date=datetime.now(),
        )
        
        # Execute workflow
        final_state = self.graph.invoke(initial_state)
        
        return final_state
