"""AI Engine model for Aegis AI."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text
from sqlalchemy.sql import func
from app.core.database import Base


class AIEngine(Base):
    """
    AI Engine model representing supported AI models/providers.
    
    Each engine has a provider, model_id, display name, costs, and encrypted API key.
    """
    __tablename__ = "ai_engines"
    
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(100), nullable=False)  # OpenAI, Anthropic, Google, xAI
    model_id = Column(String(100), nullable=False, unique=True)  # gpt-4o, claude-3-5-sonnet-latest, etc.
    display_name = Column(String(100), nullable=False)  # Human-readable name
    description = Column(Text, nullable=True)  # Model description
    input_cost = Column(Float, nullable=False, default=0.0)  # Cost per 1M input tokens
    output_cost = Column(Float, nullable=False, default=0.0)  # Cost per 1M output tokens
    api_key_encrypted = Column(String(500), nullable=True)  # Encrypted API key
    base_url = Column(String(500), nullable=True)  # Optional custom base URL
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<AIEngine(provider='{self.provider}', model_id='{self.model_id}', display_name='{self.display_name}')>"
