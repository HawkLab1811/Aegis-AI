"""
OpenAI LLM Provider adapter for Aegis AI.

Supports: gpt-4o, gpt-4o-mini, and other OpenAI models.
"""

from typing import List, Optional, Dict, Any

from app.services.llm.base import BaseLLMProvider, LLMResponse, Message


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API adapter implementing the BaseLLMProvider interface.
    
    Uses the official OpenAI Python SDK.
    """
    
    @property
    def provider_name(self) -> str:
        return "OpenAI"
    
    def _initialize_client(self):
        """Initialize the OpenAI client."""
        try:
            from openai import OpenAI
            
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            
            self._client = OpenAI(**client_kwargs)
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

            # Extract tool calls if present
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
            raise RuntimeError(f"OpenAI API error: {str(e)}")
