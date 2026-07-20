"""
User management service for Aegis AI.

Handles user CRUD operations and authentication.
Password hashing uses SHA-256 with random salt.
"""

import hashlib
import secrets
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a password with a salt. Returns (salt, hash_hex)."""
    if salt is None:
        salt = secrets.token_hex(16)
    hash_hex = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt, hash_hex


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against stored salt:hash format."""
    if not stored_hash or ":" not in stored_hash:
        return False
    salt, hash_hex = stored_hash.split(":", 1)
    _, computed = _hash_password(password, salt)
    return secrets.compare_digest(hash_hex, computed)


class UserService:
    """Service for managing users."""
    
    def __init__(self, db: Optional[Session] = None):
        self._db = db
        self._owns_session = db is None
    
    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def close(self):
        if self._owns_session and self._db is not None:
            self._db.close()
            self._db = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def create_user(
        self,
        email: str,
        name: Optional[str] = None,
        is_admin: bool = False
    ) -> User:
        existing = self.get_user_by_email(email)
        if existing:
            raise ValueError(f"User with email {email} already exists")
        
        user = User(
            email=email,
            name=name,
            is_admin=is_admin,
            is_active=True
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
    
    def get_or_create_user(
        self,
        email: str,
        name: Optional[str] = None,
        is_admin: bool = False
    ) -> User:
        user = self.get_user_by_email(email)
        if user:
            return user
        return self.create_user(email=email, name=name, is_admin=is_admin)
    
    def list_users(self, active_only: bool = True) -> List[User]:
        query = self.db.query(User)
        if active_only:
            query = query.filter(User.is_active == True)
        return query.all()
    
    def update_user(
        self,
        user_id: int,
        name: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_admin: Optional[bool] = None
    ) -> Optional[User]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        if name is not None:
            user.name = name
        if is_active is not None:
            user.is_active = is_active
        if is_admin is not None:
            user.is_admin = is_admin
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def set_password(self, user_id: int, password: str) -> Optional[User]:
        """Set password for a user (hashed with salt)."""
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        salt, hash_hex = _hash_password(password)
        user.password_hash = f"{salt}:{hash_hex}"
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def verify_password(self, user_id: int, password: str) -> bool:
        """Verify password for a user."""
        user = self.get_user_by_id(user_id)
        if not user or not user.password_hash:
            return False
        return _verify_password(password, user.password_hash)
    
    def has_admin_with_password(self) -> bool:
        """Check if any admin user has a password set (setup complete)."""
        return self.db.query(User).filter(
            User.is_admin == True,
            User.password_hash.isnot(None)
        ).count() > 0
    
    def record_login(self, user_id: int) -> Optional[User]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        user.last_login = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def delete_user(self, user_id: int) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        self.db.commit()
        
        return True
    
    def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.
        Checks password_hash in database.
        """
        user = self.get_user_by_email(email)
        if not user or not user.password_hash:
            return None
        
        if not _verify_password(password, user.password_hash):
            return None
        
        self.record_login(user.id)
        return user


def get_user_service(db: Optional[Session] = None) -> UserService:
    """Get a user service instance."""
    return UserService(db=db)
