"""MCP Server configuration model."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class MCPServer(Base):
    """MCP Server configuration for tool integration."""
    __tablename__ = "mcp_servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    command = Column(String(500), nullable=False)
    args = Column(Text, nullable=True)  # JSON array of arguments
    env_vars = Column(Text, nullable=True)  # JSON object of env vars
    proxy_enabled = Column(Boolean, default=True, nullable=False)  # CrowdStrike MCP proxy ON/OFF
    proxy_token = Column(Text, nullable=True)  # AIDR token for proxy
    proxy_url = Column(String(500), nullable=True)  # AIDR base URL template
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<MCPServer(id={self.id}, name='{self.name}', proxy={'ON' if self.proxy_enabled else 'OFF'})>"
