"""User model for Aegis AI."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """
    User model representing application users.
    
    Users are identified by email and authenticated via password_hash
    stored in the database.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)  # salt:hash format
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<User(email='{self.email}', is_admin={self.is_admin})>"
