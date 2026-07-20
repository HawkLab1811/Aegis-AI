"""RAG (Retrieval-Augmented Generation) model for Aegis AI."""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class RAG(Base):
    """
    RAG model representing RAG knowledge bases.
    
    Each RAG has a name, description, and a dedicated vector DB storage space.
    Files can be uploaded to a specific RAG.
    """
    __tablename__ = "rags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<RAG(name='{self.name}')>"


class RAGFile(Base):
    """
    RAGFile model representing files uploaded to a RAG.
    
    Each file belongs to a specific RAG and stores metadata about the uploaded file.
    media_type tracks the extraction method: document, image, video, excel, etc.
    """
    __tablename__ = "rag_files"
    
    id = Column(Integer, primary_key=True, index=True)
    rag_id = Column(Integer, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(100), nullable=True)
    media_type = Column(String(50), nullable=True)  # document, image, video, excel, csv, docx, pptx
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<RAGFile(filename='{self.filename}', rag_id={self.rag_id})>"
