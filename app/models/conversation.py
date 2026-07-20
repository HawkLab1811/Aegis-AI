"""Conversation model for per-chat memory and history."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class Conversation(Base):
    """Represents a single chat conversation with persistent history."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="New Chat")
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    engine_id = Column(Integer, ForeignKey("ai_engines.id"), nullable=True)
    collector_id = Column(Integer, ForeignKey("aidr_collectors.id"), nullable=True)
    app_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}')>"


class ConversationMessage(Base):
    """Individual message within a conversation."""
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    blocked = Column(Boolean, default=False)
    violation_reason = Column(Text, nullable=True)
    security_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ConversationMessage(id={self.id}, role='{self.role}', conv={self.conversation_id})>"
