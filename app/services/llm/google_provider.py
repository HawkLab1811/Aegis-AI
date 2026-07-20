"""
Google LLM Provider adapter for Aegis AI.

Supports: gemini-1.5-pro, gemini-1.5-flash, and other Gemini models.
"""

from typing import List, Optional, Dict, Any

from app.services.llm.base import BaseLLMProvider, LLMResponse, Message


class GoogleProvider(BaseLLMProvider):
    """
    Google Gemini API adapter implementing the BaseLLMProvider interface.
    
    Uses the Google Generative AI Python SDK.
    """
    
    @property
    def provider_name(self) -> str:
        return "Google"
    
    def _initialize_client(self):
        """Initialize the Google Generative AI client."""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model_id)
            self._genai = genai
        except ImportError:
            raise ImportError("google-generativeai package is required. Install with: pip install google-generativeai")
    
    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Message]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """
        Generate a response using Google's Gemini API.
        
        Args:
            prompt: The user's input message
            system_prompt: Optional system instructions
            history: Optional conversation history
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            LLMResponse: Standardized response object
        """
        if self._client is None:
            self._initialize_client()
        
        try:
            # Build conversation history for Gemini
            chat_history = []
            if history:
                for msg in history:
                    if msg.role == "user":
                        chat_history.append({"role": "user", "parts": [msg.content]})
                    elif msg.role == "assistant":
                        chat_history.append({"role": "model", "parts": [msg.content]})
            
            # Configure generation
            generation_config = self._genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            
            # If we have a system prompt, prepend it to the first message
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Start chat if we have history, otherwise simple generate
            if chat_history:
                chat = self._client.start_chat(history=chat_history)
                response = chat.send_message(
                    full_prompt,
                    generation_config=generation_config
                )
            else:
                response = self._client.generate_content(
                    full_prompt,
                    generation_config=generation_config
                )
            
            # Extract usage info if available
            usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage["prompt_tokens"] = getattr(response.usage_metadata, 'prompt_token_count', 0)
                usage["completion_tokens"] = getattr(response.usage_metadata, 'candidates_token_count', 0)
                usage["total_tokens"] = getattr(response.usage_metadata, 'total_token_count', 0)
            
            return LLMResponse(
                content=response.text if hasattr(response, 'text') else str(response),
                model=self.model_id,
                provider=self.provider_name,
                usage=usage,
                finish_reason="stop",
                raw_response=None
            )
        except Exception as e:
            raise RuntimeError(f"Google Gemini API error: {str(e)}")
