#!/usr/bin/env python3
"""
Clear Test Data Script for Aegis AI

This script removes all test data from the database and vector store,
preparing the system for production deployment.

Usage:
    python scripts/clear_test_data.py [--keep-admin]
    
Options:
    --keep-admin    Keep the default admin user (admin@aegis.ai)
"""

import os
import sys
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import SessionLocal, init_db, DATA_DIR
from app.models.agent import Agent
from app.models.user import User
from app.models.rag import RAG, RAGFile

# Storage paths (use the DATA_DIR from database config)
RAG_STORAGE_BASE = DATA_DIR / "rag_storage"
CHROMA_DB_PATH = DATA_DIR / "chroma_db"


def clear_test_data(keep_admin: bool = True):
    """
    Clear all test data from the database and vector store.
    
    Args:
        keep_admin: If True, keeps the admin@aegis.ai user
    """
    print("=" * 50)
    print("Aegis AI - Clear Test Data")
    print("=" * 50)
    
    # Initialize database
    init_db()
    db = SessionLocal()
    
    try:
        # --- Clear RAG Files ---
        print("\n[1/5] Clearing RAG Files...")
        rag_files = db.query(RAGFile).all()
        for rf in rag_files:
            db.delete(rf)
        print(f"  Deleted {len(rag_files)} RAG file records")
        
        # --- Clear Agents ---
        print("\n[2/5] Clearing Agents...")
        agents = db.query(Agent).all()
        for agent in agents:
            db.delete(agent)
        print(f"  Deleted {len(agents)} agent records")
        
        # --- Clear RAGs ---
        print("\n[3/5] Clearing RAGs...")
        rags = db.query(RAG).all()
        for rag in rags:
            db.delete(rag)
        print(f"  Deleted {len(rags)} RAG records")
        
        # --- Clear Users ---
        print("\n[4/5] Clearing Users...")
        if keep_admin:
            users = db.query(User).filter(User.email != "admin@aegis.ai").all()
            print("  (Keeping admin@aegis.ai)")
        else:
            users = db.query(User).all()
        for user in users:
            db.delete(user)
        print(f"  Deleted {len(users)} user records")
        
        # Commit database changes
        db.commit()
        print("\n  Database changes committed.")
        
    except Exception as e:
        db.rollback()
        print(f"\n  ERROR: {e}")
        raise
    finally:
        db.close()
    
    # --- Clear File System ---
    print("\n[5/5] Clearing file storage...")
    
    # Clear RAG storage directory
    if RAG_STORAGE_BASE.exists():
        shutil.rmtree(RAG_STORAGE_BASE)
        RAG_STORAGE_BASE.mkdir(parents=True, exist_ok=True)
        print(f"  Cleared {RAG_STORAGE_BASE}")
    
    # Clear ChromaDB vector store
    if CHROMA_DB_PATH.exists():
        shutil.rmtree(CHROMA_DB_PATH)
        CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
        print(f"  Cleared {CHROMA_DB_PATH}")
    
    print("\n" + "=" * 50)
    print("Test data cleared successfully!")
    print("=" * 50)
    
    # Show current state
    db = SessionLocal()
    try:
        print("\n--- Current State ---")
        print(f"Users: {db.query(User).count()}")
        print(f"Agents: {db.query(Agent).count()}")
        print(f"RAGs: {db.query(RAG).count()}")
        print(f"RAG Files: {db.query(RAGFile).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    keep_admin = "--keep-admin" in sys.argv or True  # Default to keeping admin
    clear_test_data(keep_admin=keep_admin)
