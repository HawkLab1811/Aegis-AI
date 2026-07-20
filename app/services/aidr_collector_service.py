"""AIDR Collector service for managing AIDR configurations."""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.aidr_collector import AIDRCollector
from app.utils.encryption import encrypt_value, decrypt_value
from app.core.database import SessionLocal


class AIDRCollectorService:
    """Service for managing AIDR Collector configurations."""

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

    def get_all(self, active_only: bool = False) -> List[AIDRCollector]:
        """Get all AIDR collectors."""
        query = self.db.query(AIDRCollector)
        if active_only:
            query = query.filter(AIDRCollector.is_active == True)
        return query.order_by(AIDRCollector.name).all()

    def get_by_id(self, collector_id: int) -> Optional[AIDRCollector]:
        """Get AIDR collector by ID."""
        return self.db.query(AIDRCollector).filter(AIDRCollector.id == collector_id).first()

    def get_by_name(self, name: str) -> Optional[AIDRCollector]:
        """Get AIDR collector by name."""
        return self.db.query(AIDRCollector).filter(AIDRCollector.name == name).first()

    def get_default(self) -> Optional[AIDRCollector]:
        """Get the default AIDR collector."""
        return self.db.query(AIDRCollector).filter(
            AIDRCollector.is_default == True,
            AIDRCollector.is_active == True
        ).first()

    def create(
        self,
        name: str,
        token: str,
        url: str = "https://api.crowdstrike.com/aidr/aiguard",
        description: Optional[str] = None,
        is_default: bool = False
    ) -> AIDRCollector:
        """Create a new AIDR collector with encrypted token."""
        # Encrypt the token before storing
        encrypted_token = encrypt_value(token)
        
        # If this is set as default, unset other defaults
        if is_default:
            self.db.query(AIDRCollector).filter(
                AIDRCollector.is_default == True
            ).update({"is_default": False})
        
        collector = AIDRCollector(
            name=name,
            description=description,
            token=encrypted_token,
            url=url,
            is_default=is_default,
            is_active=True
        )
        
        self.db.add(collector)
        self.db.commit()
        self.db.refresh(collector)
        return collector

    def update(
        self,
        collector_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        token: Optional[str] = None,
        url: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_default: Optional[bool] = None
    ) -> Optional[AIDRCollector]:
        """Update an AIDR collector."""
        collector = self.get_by_id(collector_id)
        if not collector:
            return None
        
        if name is not None:
            collector.name = name
        if description is not None:
            collector.description = description
        if token is not None:
            collector.token = encrypt_value(token)
        if url is not None:
            collector.url = url
        if is_active is not None:
            collector.is_active = is_active
        if is_default is not None:
            if is_default:
                # Unset other defaults
                self.db.query(AIDRCollector).filter(
                    AIDRCollector.id != collector_id,
                    AIDRCollector.is_default == True
                ).update({"is_default": False})
            collector.is_default = is_default
        
        self.db.commit()
        self.db.refresh(collector)
        return collector

    def delete(self, collector_id: int) -> bool:
        """Soft delete an AIDR collector (deactivate)."""
        collector = self.get_by_id(collector_id)
        if not collector:
            return False
        
        collector.is_active = False
        if collector.is_default:
            collector.is_default = False
        
        self.db.commit()
        return True

    def hard_delete(self, collector_id: int) -> bool:
        """Permanently delete an AIDR collector."""
        collector = self.get_by_id(collector_id)
        if not collector:
            return False
        
        self.db.delete(collector)
        self.db.commit()
        return True

    def get_decrypted_token(self, collector_id: int) -> Optional[str]:
        """Get the decrypted token for a collector."""
        collector = self.get_by_id(collector_id)
        if not collector or not collector.token:
            return None
        
        try:
            return decrypt_value(collector.token)
        except Exception:
            return None

    def get_collector_config(self, collector_id: int) -> Optional[dict]:
        """Get the full configuration for a collector (with decrypted token)."""
        collector = self.get_by_id(collector_id)
        if not collector:
            return None
        
        token = self.get_decrypted_token(collector_id)
        
        return {
            "id": collector.id,
            "name": collector.name,
            "description": collector.description,
            "token": token,
            "url": collector.url,
            "is_active": collector.is_active,
            "is_default": collector.is_default
        }
