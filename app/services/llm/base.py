"""
Base LLM Provider abstract class for Aegis AI.

This module defines the adapter pattern interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class LLMResponse:
    """Standard response structure from LLM providers."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int]  # {"prompt_tokens": x, "completion_tokens": y, "total_tokens": z}
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None  # Parsed tool calls if any


@dataclass
class Message:
    """Standard message format for chat history."""
    role: str  # "system", "user", "assistant"
    content: str


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All provider adapters (OpenAI, Anthropic, Google, xAI) must inherit from this
    class and implement the required methods.
    
    The adapter pattern allows:
    - Unified interface for all providers
    - Easy switching between providers
    - Consistent error handling
    - API key management through encrypted storage
    """
    
    def __init__(self, api_key: str, model_id: str, base_url: Optional[str] = None):
        """
        Initialize the LLM provider.
        
        Args:
            api_key: Decrypted API key for authentication
            model_id: The model identifier (e.g., "gpt-4o", "claude-3-5-sonnet-latest")
            base_url: Optional custom base URL for the API
        """
        self.api_key = api_key
        self.model_id = model_id
        self.base_url = base_url
        self._client = None
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'OpenAI', 'Anthropic')."""
        pass
    
    @abstractmethod
    def _initialize_client(self):
        """Initialize the provider-specific client."""
        pass
    
    @abstractmethod
    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Message]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        This is the main method that all providers must implement.

        Args:
            prompt: The user's input message
            system_prompt: Optional system instructions
            history: Optional conversation history
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens in response
            tools: Optional list of tool schemas for function calling

        Returns:
            LLMResponse: Standardized response object

        Raises:
            Exception: Provider-specific errors should be caught and re-raised
                      with meaningful messages
        """
        pass
    
    def _build_messages(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Message]] = None
    ) -> List[Dict[str, str]]:
        """
        Build the messages array for the API request.
        
        Args:
            prompt: The user's input message
            system_prompt: Optional system instructions
            history: Optional conversation history
            
        Returns:
            List of message dictionaries
        """
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add history if provided
        if history:
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})
        
        # Add current user prompt
        messages.append({"role": "user", "content": prompt})
        
        return messages
    
    def validate_api_key(self) -> bool:
        """
        Validate that the API key is set and non-empty.
        
        Returns:
            bool: True if API key appears valid
        """
        return bool(self.api_key and len(self.api_key) > 10)
