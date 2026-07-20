"""AIDR Collector model for managing multiple AIDR configurations."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func

from app.core.database import Base


class AIDRCollector(Base):
    """AIDR Collector configurations for CrowdStrike AI Guard."""
    __tablename__ = "aidr_collectors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    token = Column(Text, nullable=False)  # Encrypted AIDR token
    url = Column(String(500), nullable=False, default="https://api.crowdstrike.com/aidr/aiguard")
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<AIDRCollector(id={self.id}, name='{self.name}')>"
