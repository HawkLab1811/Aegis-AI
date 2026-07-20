"""
RAG management service for Aegis AI.

Handles RAG and RAGFile CRUD operations.
"""

import os
from typing import Optional, List
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.rag import RAG, RAGFile


# Project root for fallback
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Data directory - can be overridden by DATA_DIR environment variable
# For Docker, mount a volume at /app/data
DATA_DIR = Path(os.environ.get("DATA_DIR", str(PROJECT_ROOT / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Base directory for RAG file storage
RAG_STORAGE_BASE = DATA_DIR / "rag_storage"


class RAGService:
    """Service for managing RAG knowledge bases and files."""
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the RAG service.
        
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
    
    # ============================================================
    # RAG Operations
    # ============================================================
    def create_rag(
        self,
        name: str,
        description: Optional[str] = None
    ) -> RAG:
        """
        Create a new RAG knowledge base.
        
        Args:
            name: RAG name (must be unique)
            description: RAG description
            
        Returns:
            Created RAG object
            
        Raises:
            ValueError: If RAG with name already exists
        """
        existing = self.get_rag_by_name(name)
        if existing:
            raise ValueError(f"RAG with name '{name}' already exists")
        
        rag = RAG(
            name=name,
            description=description,
            is_active=True
        )
        
        self.db.add(rag)
        self.db.commit()
        self.db.refresh(rag)
        
        # Create storage directory for this RAG
        rag_dir = RAG_STORAGE_BASE / str(rag.id)
        rag_dir.mkdir(parents=True, exist_ok=True)
        
        return rag
    
    def get_rag_by_id(self, rag_id: int) -> Optional[RAG]:
        """Get RAG by ID."""
        return self.db.query(RAG).filter(RAG.id == rag_id).first()
    
    def get_rag_by_name(self, name: str) -> Optional[RAG]:
        """Get RAG by name."""
        return self.db.query(RAG).filter(RAG.name == name).first()
    
    def list_rags(self, active_only: bool = True) -> List[RAG]:
        """List all RAGs."""
        query = self.db.query(RAG)
        if active_only:
            query = query.filter(RAG.is_active == True)
        return query.order_by(RAG.name).all()
    
    def update_rag(
        self,
        rag_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[RAG]:
        """Update RAG attributes."""
        rag = self.get_rag_by_id(rag_id)
        if not rag:
            return None
        
        if name is not None:
            # Check for name uniqueness if changing name
            existing = self.get_rag_by_name(name)
            if existing and existing.id != rag_id:
                raise ValueError(f"RAG with name '{name}' already exists")
            rag.name = name
        if description is not None:
            rag.description = description
        if is_active is not None:
            rag.is_active = is_active
        
        self.db.commit()
        self.db.refresh(rag)
        
        return rag
    
    def delete_rag(self, rag_id: int) -> bool:
        """Delete a RAG (soft delete)."""
        rag = self.get_rag_by_id(rag_id)
        if not rag:
            return False
        
        rag.is_active = False
        self.db.commit()
        
        return True
    
    # ============================================================
    # RAG File Operations
    # ============================================================
    def add_file(
        self,
        rag_id: int,
        filename: str,
        file_path: str,
        file_size: int,
        file_type: Optional[str] = None,
        media_type: Optional[str] = None
    ) -> RAGFile:
        """
        Add a file record to a RAG.
        
        Args:
            rag_id: ID of the RAG to add file to
            filename: Original filename
            file_path: Path where file is stored
            file_size: Size of file in bytes
            file_type: MIME type or file extension
            media_type: Extraction type (document, image, video, excel, csv, docx, pptx, pdf)
            
        Returns:
            Created RAGFile object
        """
        rag_file = RAGFile(
            rag_id=rag_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            media_type=media_type,
            is_processed=False
        )
        
        self.db.add(rag_file)
        self.db.commit()
        self.db.refresh(rag_file)
        
        return rag_file
    
    def get_file_by_id(self, file_id: int) -> Optional[RAGFile]:
        """Get RAG file by ID."""
        return self.db.query(RAGFile).filter(RAGFile.id == file_id).first()
    
    def list_files_by_rag(self, rag_id: int) -> List[RAGFile]:
        """List all files for a specific RAG."""
        return self.db.query(RAGFile).filter(RAGFile.rag_id == rag_id).order_by(RAGFile.created_at.desc()).all()
    
    def delete_file(self, file_id: int) -> bool:
        """Delete a RAG file record (and optionally the actual file)."""
        rag_file = self.get_file_by_id(file_id)
        if not rag_file:
            return False
        
        # Delete from database
        self.db.delete(rag_file)
        self.db.commit()
        
        return True
    
    def mark_file_processed(self, file_id: int) -> Optional[RAGFile]:
        """Mark a file as processed (vectorized)."""
        rag_file = self.get_file_by_id(file_id)
        if not rag_file:
            return None
        
        rag_file.is_processed = True
        self.db.commit()
        self.db.refresh(rag_file)
        
        return rag_file
    
    def get_rag_storage_path(self, rag_id: int) -> Path:
        """Get the storage directory path for a specific RAG."""
        rag_dir = RAG_STORAGE_BASE / str(rag_id)
        rag_dir.mkdir(parents=True, exist_ok=True)
        return rag_dir


def get_rag_service(db: Optional[Session] = None) -> RAGService:
    """Get a RAG service instance."""
    return RAGService(db=db)
