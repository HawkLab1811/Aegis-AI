"""
xAI LLM Provider adapter for Aegis AI.

Supports: grok-2 and other xAI Grok models.
xAI uses an OpenAI-compatible API.
"""

from typing import List, Optional, Dict, Any

from app.services.llm.base import BaseLLMProvider, LLMResponse, Message


class XAIProvider(BaseLLMProvider):
    """
    xAI (Grok) API adapter implementing the BaseLLMProvider interface.
    
    xAI's API is OpenAI-compatible, so we use the OpenAI SDK with a custom base URL.
    """
    
    DEFAULT_BASE_URL = "https://api.x.ai/v1"
    
    @property
    def provider_name(self) -> str:
        return "xAI"
    
    def _initialize_client(self):
        """Initialize the xAI client using OpenAI SDK."""
        try:
            from openai import OpenAI
            
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url or self.DEFAULT_BASE_URL
            )
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")
    
    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Message]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> LLMResponse:
        if self._client is None:
            self._initialize_client()

        messages = self._build_messages(prompt, system_prompt, history)

        try:
            kwargs = {
                "model": self.model_id,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]

            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = []
                for tc in choice.message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                provider=self.provider_name,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                finish_reason=choice.finish_reason,
                raw_response=response.model_dump() if hasattr(response, 'model_dump') else None,
                tool_calls=tool_calls
            )
        except Exception as e:
            raise RuntimeError(f"xAI API error: {str(e)}")
