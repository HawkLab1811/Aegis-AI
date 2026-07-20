"""Profile model for saving user configuration presets."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class Profile(Base):
    """User profiles for saving configuration presets."""
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    
    # Configuration references (nullable - None means use default)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    engine_id = Column(Integer, ForeignKey("ai_engines.id", ondelete="SET NULL"), nullable=True)
    collector_id = Column(Integer, ForeignKey("aidr_collectors.id", ondelete="SET NULL"), nullable=True)
    app_name = Column(String(255), nullable=True)  # Application name string
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Profile(id={self.id}, name='{self.name}')>"
