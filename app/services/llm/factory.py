"""
LLM Provider Factory for Aegis AI.

This module provides a factory function to instantiate the appropriate
LLM provider based on the provider name, with support for encrypted API keys.
"""

from typing import Optional

from app.services.llm.base import BaseLLMProvider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.google_provider import GoogleProvider
from app.services.llm.xai_provider import XAIProvider
from app.services.llm.mimo_provider import MiMoProvider
from app.core.config import decrypt_value


# Mapping of provider names to their adapter classes
PROVIDER_MAP = {
    "OpenAI": OpenAIProvider,
    "Anthropic": AnthropicProvider,
    "Google": GoogleProvider,
    "xAI": XAIProvider,
    "MiMo": MiMoProvider,
}


def get_provider(
    provider_name: str,
    model_id: str,
    api_key: str,
    encrypted: bool = True,
    base_url: Optional[str] = None
) -> BaseLLMProvider:
    """
    Factory function to get the appropriate LLM provider.
    
    Args:
        provider_name: The provider name (OpenAI, Anthropic, Google, xAI)
        model_id: The model identifier
        api_key: The API key (encrypted by default)
        encrypted: Whether the API key is encrypted (default: True)
        base_url: Optional custom base URL
        
    Returns:
        BaseLLMProvider: An instance of the appropriate provider
        
    Raises:
        ValueError: If the provider is not supported
    """
    if provider_name not in PROVIDER_MAP:
        raise ValueError(f"Unsupported provider: {provider_name}. Supported: {list(PROVIDER_MAP.keys())}")
    
    # Decrypt API key if encrypted
    decrypted_key = decrypt_value(api_key) if encrypted else api_key
    
    # Instantiate and return the provider
    provider_class = PROVIDER_MAP[provider_name]
    return provider_class(
        api_key=decrypted_key,
        model_id=model_id,
        base_url=base_url
    )


def get_provider_from_engine(engine) -> BaseLLMProvider:
    """
    Create a provider instance from an AIEngine database model.
    
    Args:
        engine: AIEngine model instance with api_key_encrypted set
        
    Returns:
        BaseLLMProvider: An instance of the appropriate provider
        
    Raises:
        ValueError: If the engine has no API key configured
    """
    if not engine.api_key_encrypted:
        raise ValueError(f"No API key configured for engine: {engine.display_name}")
    
    return get_provider(
        provider_name=engine.provider,
        model_id=engine.model_id,
        api_key=engine.api_key_encrypted,
        encrypted=True,
        base_url=engine.base_url
    )
