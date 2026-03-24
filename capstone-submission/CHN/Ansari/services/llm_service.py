"""
LLM service for interacting with language models.
Supports OpenAI API, Groq API, and mock mode for testing.
Includes retry logic and error handling.
"""
import json
import logging
import time
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from config.settings import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TIMEOUT,
    LLM_RETRY_ATTEMPTS,
    MOCK_MODE,
)

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when LLM call fails."""
    pass


class LLMInterface(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def call(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Call the LLM with given prompts.
        
        Args:
            system_prompt: System message to set context
            user_message: User input message
            temperature: Model temperature (0-1)
            max_tokens: Max tokens in response
            
        Returns:
            LLM response text
        """
        pass
    
    @abstractmethod
    def call_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Call the LLM and parse JSON response.
        
        Args:
            system_prompt: System message to set context
            user_message: User input message
            temperature: Model temperature (0-1)
            max_tokens: Max tokens in response
            
        Returns:
            Parsed JSON response as dictionary
        """
        pass


class OpenAILLM(LLMInterface):
    """OpenAI language model interface."""
    
    def __init__(
        self,
        api_key: str = OPENAI_API_KEY,
        model: str = OPENAI_MODEL,
        temperature: float = LLM_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
    ):
        """
        Initialize OpenAI LLM.
        
        Args:
            api_key: OpenAI API key
            model: Model name
            temperature: Model temperature
            max_tokens: Max tokens
        """
        if not api_key:
            raise LLMError("OpenAI API key is required")
        
        self.client = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=LLM_TIMEOUT,
        )
        self.model = model
    
    def call(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call OpenAI API with retry logic."""
        for attempt in range(LLM_RETRY_ATTEMPTS):
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_message),
                ]
                response = self.client.invoke(
                    messages,
                    temperature=temperature or LLM_TEMPERATURE,
                    max_tokens=max_tokens or LLM_MAX_TOKENS,
                )
                return response.content
            
            except Exception as e:
                logger.warning(f"LLM call attempt {attempt + 1} failed: {str(e)}")
                if attempt < LLM_RETRY_ATTEMPTS - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise LLMError(f"LLM call failed after {LLM_RETRY_ATTEMPTS} attempts: {str(e)}")
    
    def call_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Call OpenAI API and parse JSON response."""
        response = self.call(system_prompt, user_message, temperature, max_tokens)
        
        try:
            # Try to extract JSON from response
            # LLM might include markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse LLM response as JSON: {str(e)}\nResponse: {response}")


class GroqLLM(LLMInterface):
    """Groq language model interface."""
    
    def __init__(
        self,
        api_key: str = GROQ_API_KEY,
        model: str = GROQ_MODEL,
        temperature: float = LLM_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
    ):
        """
        Initialize Groq LLM.
        
        Args:
            api_key: Groq API key
            model: Model name
            temperature: Model temperature
            max_tokens: Max tokens
        """
        if not api_key:
            raise LLMError("Groq API key is required")
        
        self.client = ChatGroq(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=LLM_TIMEOUT,
        )
        self.model = model
    
    def call(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call Groq API with retry logic."""
        for attempt in range(LLM_RETRY_ATTEMPTS):
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_message),
                ]
                response = self.client.invoke(
                    messages,
                    temperature=temperature or LLM_TEMPERATURE,
                    max_tokens=max_tokens or LLM_MAX_TOKENS,
                )
                return response.content
            
            except Exception as e:
                logger.warning(f"Groq call attempt {attempt + 1} failed: {str(e)}")
                if attempt < LLM_RETRY_ATTEMPTS - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise LLMError(f"Groq call failed after {LLM_RETRY_ATTEMPTS} attempts: {str(e)}")
    
    def call_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Call Groq API and parse JSON response."""
        response = self.call(system_prompt, user_message, temperature, max_tokens)
        
        try:
            # Try to extract JSON from response
            # LLM might include markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse Groq response as JSON: {str(e)}\nResponse: {response}")


class MockLLM(LLMInterface):
    """Mock LLM for testing without API calls."""
    
    def __init__(self):
        """Initialize Mock LLM."""
        logger.info("Using Mock LLM for testing")
    
    def call(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Return mock response."""
        return "This is a mock LLM response for testing purposes."
    
    def call_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return mock JSON response based on prompt context."""
        # Simple heuristics to return appropriate mock responses
        if "classification" in user_message.lower():
            return {
                "classification": "CEASE",
                "confidence": 0.95,
                "reasoning": "Mock classification: Document appears to be a cease and desist letter."
            }
        elif "extract" in user_message.lower():
            return {
                "sender_name": "Mock Company Inc.",
                "sender_address": "123 Legal Street, Law City, LC 12345",
                "request_date": "2026-03-21",
                "intent_summary": "Mock extraction: Cease use of trademark",
                "key_claims": ["Trademark infringement", "Brand violation"],
                "requested_actions": ["Remove logo", "Cease operations"],
                "deadline": "2026-04-21",
                "legal_references": ["Trademark Act", "Patent Law"]
            }
        else:
            return {"result": "Mock response"}


def get_llm() -> LLMInterface:
    """
    Factory function to get appropriate LLM instance.
    
    Returns:
        LLMInterface instance (OpenAI, Groq, or Mock)
        
    Raises:
        LLMError: If configuration is invalid
    """
    if MOCK_MODE:
        return MockLLM()
    elif LLM_PROVIDER == "openai":
        return OpenAILLM()
    elif LLM_PROVIDER == "groq":
        return GroqLLM()
    else:
        raise LLMError(f"Unknown LLM provider: {LLM_PROVIDER}. Use 'openai', 'groq', or 'mock'")


# Global LLM instance
_llm_instance: Optional[LLMInterface] = None


def get_llm_instance() -> LLMInterface:
    """
    Get or create global LLM instance (singleton).
    
    Returns:
        LLMInterface instance
    """
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = get_llm()
    return _llm_instance
