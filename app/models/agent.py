"""Agent model for Aegis AI."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base


class Agent(Base):
    """
    Agent model representing AI assistants/agents.
    
    Each agent has a name, description, system prompt, and optionally
    links to a RAG knowledge base and an MCP server.
    """
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    rag_id = Column(Integer, ForeignKey("rags.id"), nullable=True)
    mcp_server_id = Column(Integer, ForeignKey("mcp_servers.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Agent(name='{self.name}')>"
