"""Test Repository model for AIDR policy testing samples."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class TestRepositoryItem(Base):
    """Pre-built test samples for AIDR policy validation."""
    __tablename__ = "test_repository"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    prompt_text = Column(Text, nullable=False)
    severity = Column(String(20), nullable=True)  # low, medium, high, critical
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TestRepositoryItem(category='{self.category}', name='{self.name}')>"
