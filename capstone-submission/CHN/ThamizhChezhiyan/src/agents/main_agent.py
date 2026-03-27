"""
Main Agent - LLM-powered agent for document processing using LangChain
"""
from typing import Dict, Any, List
from langchain_core.tools import Tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import logging
from pathlib import Path

from src.config.config import GROQ_API_KEY, MODEL_NAME
from src.agents.classification_agent import ClassificationAgent
from src.tools.document_loader import DocumentProcesser
from src.tools.audit_logger import get_audit_trail

logger = logging.getLogger(__name__)


class DocumentProcessingAgent:
    """Main LLM-powered agent for document processing"""

    def __init__(self, streaming: bool = True):
        """Initialize the agent with LLM and tools"""
        self.streaming = streaming
        self.audit_trail = get_audit_trail()

        # Initialize LLM
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=MODEL_NAME,
            temperature=0.1,
            streaming=streaming,
            callbacks=[StreamingStdOutCallbackHandler()] if streaming else []
        )

        # Classification uses the same LLM client
        self.classifier = ClassificationAgent(self.llm)

        # Initialize tools
        self.tools = [
            Tool(
                name="pdf_loader",
                func=self._run_pdf_loader,
                description="Load and extract text from PDF documents. Input: file path"
            ),
            Tool(
                name="text_extractor", 
                func=self._run_text_extractor,
                description="Extract text from documents (PDF, images, text files). Input: file path"
            ),
            Tool(
                name="document_classifier",
                func=self._run_document_classifier,
                description="Classify document content as Cease (valid request), Uncertain (needs review), or Irrelevant. Input: document content text"
            )
        ]

        # System prompt
        self.system_prompt = """You are an intelligent Document Processing Agent specializing in Cease & Desist document analysis.

Your capabilities:
- Load and extract text from PDF documents and other formats
- Classify documents as Cease (valid requests), Uncertain (needs human review), or Irrelevant
- Process documents according to compliance and legal standards
- Maintain audit trails for all actions
- Handle document processing workflows

When processing documents:
1. First extract text from the document
2. Analyze the content for cease & desist indicators
3. Classify appropriately based on legal criteria
4. Provide clear explanations for your decisions
5. Log all actions for compliance

Always be thorough, accurate, and maintain professional standards. If uncertain, recommend human review.

You have access to tools for:
- pdf_loader: Load PDF documents
- text_extractor: Extract text from various formats
- document_classifier: Classify document content

Use these tools when needed to help users with document processing tasks."""

        # Chat history
        self.chat_history: List[BaseMessage] = []

        logger.info("Document Processing Agent initialized")

    def _run_pdf_loader(self, file_path: str) -> str:
        """Load PDF and return extracted content preview."""
        try:
            if not Path(file_path).exists():
                return f"Error: File not found: {file_path}"

            content = DocumentProcesser.extract_text(file_path)
            if content:
                return (
                    f"Successfully loaded PDF. Content length: {len(content)} characters\n\n"
                    f"{content[:1000]}..."
                )
            return "Error: Could not extract text from PDF"
        except Exception as e:
            return f"Error loading PDF: {str(e)}"

    def _run_text_extractor(self, file_path: str) -> str:
        """Extract text from supported document formats."""
        try:
            if not Path(file_path).exists():
                return f"Error: File not found: {file_path}"

            content = DocumentProcesser.extract_text(file_path)
            if content:
                return (
                    f"Successfully extracted text. Content length: {len(content)} characters\n\n"
                    f"{content[:1000]}..."
                )
            return "Error: Could not extract text from document"
        except Exception as e:
            return f"Error extracting text: {str(e)}"

    def _run_document_classifier(self, content: str) -> str:
        """Classify the provided document content."""
        try:
            result = self.classifier.classify_document("temp_doc", content)
            indicators = ", ".join(result.key_indicators)
            return (
                f"Classification: {result.classification}\n"
                f"Confidence: {result.confidence:.2%}\n"
                f"Explanation: {result.explanation}\n"
                f"Key Indicators: {indicators}"
            )
        except Exception as e:
            return f"Error classifying document: {str(e)}"

    def process_message(self, user_input: str) -> str:
        """
        Process a user message and return response

        Args:
            user_input: User's message

        Returns:
            Agent's response
        """
        try:
            # Log the interaction
            self.audit_trail.log_action(
                agent_name="MainAgent",
                action="Process Message",
                document_name="chat_interaction",
                explanation=f"User input: {user_input[:100]}...",
                status="processing"
            )

            # Create prompt with tools and history
            tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
            
            full_prompt = f"""{self.system_prompt}

Available tools:
{tool_descriptions}

Chat History:
{chr(10).join([f"{msg.type}: {msg.content}" for msg in self.chat_history[-6:]])}

Human: {user_input}

Assistant: Let me think step by step about how to help with this request."""

            # Get LLM response
            response = self.llm.invoke(full_prompt)

            # Update chat history
            self.chat_history.append(HumanMessage(content=user_input))
            self.chat_history.append(AIMessage(content=response.content))

            # Keep history manageable
            if len(self.chat_history) > 20:
                self.chat_history = self.chat_history[-20:]

            # Log completion
            self.audit_trail.log_action(
                agent_name="MainAgent",
                action="Process Message",
                document_name="chat_interaction",
                explanation=f"Response generated: {response.content[:100]}...",
                status="completed"
            )

            return response.content

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_msg = f"I apologize, but I encountered an error: {str(e)}"
            self.audit_trail.log_action(
                agent_name="MainAgent",
                action="Process Message",
                document_name="chat_interaction",
                status="error",
                explanation=str(e)
            )
            return error_msg

    def process_document_streaming(self, document_path: str) -> str:
        """
        Process a document with streaming updates

        Args:
            document_path: Path to document

        Returns:
            Processing result
        """
        try:
            # First, load the document
            if self.streaming:
                print("🔄 Loading document...")

            load_prompt = f"Please load and analyze this document: {document_path}"
            result = self.process_message(load_prompt)

            if self.streaming:
                print("✅ Document loaded successfully")
                print("🔄 Classifying document...")

            # Then classify
            classify_prompt = f"Based on the loaded document content, please classify it as Cease, Uncertain, or Irrelevant."
            classification = self.process_message(classify_prompt)

            if self.streaming:
                print("✅ Classification complete")

            return f"Document Processing Complete:\n\n{classification}"

        except Exception as e:
            logger.error(f"Error in streaming document processing: {e}")
            return f"Error processing document: {str(e)}"

    def get_status(self) -> Dict[str, Any]:
        """Get agent status and capabilities"""
        return {
            "agent_type": "LLM-powered Document Processing Agent",
            "llm_model": MODEL_NAME,
            "streaming_enabled": self.streaming,
            "tools_available": [tool.name for tool in self.tools],
            "chat_history_length": len(self.chat_history),
            "system_prompt": self.system_prompt[:200] + "..."
        }
