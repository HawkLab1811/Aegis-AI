"""
AI Engine management service for Aegis AI.

Handles AI Engine CRUD operations with encrypted API key storage.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.ai_engine import AIEngine
from app.core.config import encrypt_value, decrypt_value


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt API key using Fernet."""
    return encrypt_value(plaintext)


def decrypt_api_key(ciphertext: str) -> str:
    """Decrypt API key using Fernet."""
    return decrypt_value(ciphertext)


class AIEngineService:
    """
    Service for managing AI Engines.
    
    API keys are automatically encrypted when stored and
    decrypted when retrieved.
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the AI engine service.
        
        Args:
            db: Optional database session (for dependency injection/testing)
        """
        self._db = db
        self._owns_session = db is None
    
    @property
    def db(self) -> Session:
        """Get or create database session."""
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def close(self):
        """Close the database session if we own it."""
        if self._owns_session and self._db is not None:
            self._db.close()
            self._db = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def get_engine_by_id(self, engine_id: int) -> Optional[AIEngine]:
        """
        Get AI engine by ID.
        
        Args:
            engine_id: Engine's database ID
            
        Returns:
            AIEngine object or None if not found
        """
        return self.db.query(AIEngine).filter(AIEngine.id == engine_id).first()
    
    def get_engine_by_name(self, name: str) -> Optional[AIEngine]:
        """
        Get AI engine by name.
        
        Args:
            name: Engine name (e.g., "OpenAI", "Anthropic")
            
        Returns:
            AIEngine object or None if not found
        """
        return self.db.query(AIEngine).filter(AIEngine.name == name).first()
    
    def list_engines(self, active_only: bool = True) -> List[AIEngine]:
        """
        List all AI engines.
        
        Args:
            active_only: If True, only return active engines
            
        Returns:
            List of AIEngine objects
        """
        query = self.db.query(AIEngine)
        if active_only:
            query = query.filter(AIEngine.is_active == True)
        return query.all()
    
    def set_api_key(self, engine_id: int, api_key: str) -> Optional[AIEngine]:
        """
        Set (encrypt and store) API key for an engine.
        
        The API key is encrypted using Fernet before storage.
        
        Args:
            engine_id: Engine's database ID
            api_key: Plaintext API key to encrypt and store
            
        Returns:
            Updated AIEngine object or None if not found
        """
        engine = self.get_engine_by_id(engine_id)
        if not engine:
            return None
        
        # Encrypt the API key before storing
        encrypted_key = encrypt_api_key(api_key)
        engine.api_key_encrypted = encrypted_key
        
        self.db.commit()
        self.db.refresh(engine)
        
        return engine
    
    def set_api_key_by_name(self, name: str, api_key: str) -> Optional[AIEngine]:
        """
        Set API key for an engine by name.
        
        Args:
            name: Engine name (e.g., "OpenAI")
            api_key: Plaintext API key to encrypt and store
            
        Returns:
            Updated AIEngine object or None if not found
        """
        engine = self.get_engine_by_name(name)
        if not engine:
            return None
        
        return self.set_api_key(engine.id, api_key)
    
    def get_api_key(self, engine_id: int) -> Optional[str]:
        """
        Get (decrypt) API key for an engine.
        
        Args:
            engine_id: Engine's database ID
            
        Returns:
            Decrypted plaintext API key or None if not found/set
        """
        engine = self.get_engine_by_id(engine_id)
        if not engine or not engine.api_key_encrypted:
            return None
        
        return decrypt_api_key(engine.api_key_encrypted)
    
    def get_api_key_by_name(self, name: str) -> Optional[str]:
        """
        Get API key for an engine by name.
        
        Args:
            name: Engine name (e.g., "OpenAI")
            
        Returns:
            Decrypted plaintext API key or None if not found/set
        """
        engine = self.get_engine_by_name(name)
        if not engine:
            return None
        
        return self.get_api_key(engine.id)
    
    def has_api_key(self, engine_id: int) -> bool:
        """
        Check if an engine has an API key configured.
        
        Args:
            engine_id: Engine's database ID
            
        Returns:
            True if API key is set, False otherwise
        """
        engine = self.get_engine_by_id(engine_id)
        return engine is not None and engine.api_key_encrypted is not None
    
    def clear_api_key(self, engine_id: int) -> Optional[AIEngine]:
        """
        Remove API key from an engine.
        
        Args:
            engine_id: Engine's database ID
            
        Returns:
            Updated AIEngine object or None if not found
        """
        engine = self.get_engine_by_id(engine_id)
        if not engine:
            return None
        
        engine.api_key_encrypted = None
        self.db.commit()
        self.db.refresh(engine)
        
        return engine
    
    def update_engine(
        self,
        engine_id: int,
        base_url: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[AIEngine]:
        """
        Update engine attributes.
        
        Args:
            engine_id: Engine's database ID
            base_url: New base URL (if provided)
            is_active: New active status (if provided)
            
        Returns:
            Updated AIEngine object or None if not found
        """
        engine = self.get_engine_by_id(engine_id)
        if not engine:
            return None
        
        if base_url is not None:
            engine.base_url = base_url
        if is_active is not None:
            engine.is_active = is_active
        
        self.db.commit()
        self.db.refresh(engine)
        
        return engine
    
    def get_raw_encrypted_key(self, engine_id: int) -> Optional[str]:
        """
        Get the raw encrypted API key (for verification/debugging).
        
        This returns the ciphertext as stored in the database,
        NOT the decrypted plaintext.
        
        Args:
            engine_id: Engine's database ID
            
        Returns:
            Encrypted API key ciphertext or None if not found/set
        """
        engine = self.get_engine_by_id(engine_id)
        if not engine:
            return None
        return engine.api_key_encrypted


# Convenience function
def get_ai_engine_service(db: Optional[Session] = None) -> AIEngineService:
    """Get an AI engine service instance."""
    return AIEngineService(db=db)
