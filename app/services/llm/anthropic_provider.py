"""
Anthropic LLM Provider adapter for Aegis AI.

Supports: claude-3-5-sonnet-latest, claude-3-opus-latest, and other Claude models.
"""

from typing import List, Optional, Dict, Any

from app.services.llm.base import BaseLLMProvider, LLMResponse, Message


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic API adapter implementing the BaseLLMProvider interface.
    
    Uses the official Anthropic Python SDK.
    """
    
    @property
    def provider_name(self) -> str:
        return "Anthropic"
    
    def _initialize_client(self):
        """Initialize the Anthropic client."""
        try:
            from anthropic import Anthropic
            
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            
            self._client = Anthropic(**client_kwargs)
        except ImportError:
            raise ImportError("anthropic package is required. Install with: pip install anthropic")
    
    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Message]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """
        Generate a response using Anthropic's API.
        
        Note: Anthropic's API handles system prompts differently - they go in
        a separate 'system' parameter, not in messages.
        
        Args:
            prompt: The user's input message
            system_prompt: Optional system instructions
            history: Optional conversation history
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            LLMResponse: Standardized response object
        """
        if self._client is None:
            self._initialize_client()
        
        # Build messages (without system prompt - Anthropic handles it separately)
        messages = []
        if history:
            for msg in history:
                if msg.role != "system":
                    messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": prompt})
        
        try:
            request_kwargs = {
                "model": self.model_id,
                "messages": messages,
                "temperature": min(temperature, 1.0),  # Anthropic max is 1.0
                "max_tokens": max_tokens
            }
            
            if system_prompt:
                request_kwargs["system"] = system_prompt
            
            response = self._client.messages.create(**request_kwargs)
            
            # Extract content from response
            content = ""
            if response.content:
                content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
            
            return LLMResponse(
                content=content,
                model=response.model,
                provider=self.provider_name,
                usage={
                    "prompt_tokens": response.usage.input_tokens if response.usage else 0,
                    "completion_tokens": response.usage.output_tokens if response.usage else 0,
                    "total_tokens": (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0
                },
                finish_reason=response.stop_reason,
                raw_response=response.model_dump() if hasattr(response, 'model_dump') else None
            )
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {str(e)}")
