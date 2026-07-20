"""
Database configuration and seeding for Aegis AI.

This module handles:
- SQLAlchemy engine and session setup
- Database initialization
- Seeding of AI_Engines with pre-configured models
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Data directory - can be overridden by DATA_DIR environment variable
# For Docker, mount a volume at /app/data
DATA_DIR = Path(os.environ.get("DATA_DIR", str(PROJECT_ROOT / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "aegis.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency for getting database sessions.
    
    Yields:
        Session: SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database, creating all tables."""
    # Import all models to ensure they are registered with Base
    from app.models.ai_engine import AIEngine
    from app.models.user import User
    from app.models.agent import Agent
    from app.models.rag import RAG, RAGFile
    from app.models.application import Application
    from app.models.aidr_collector import AIDRCollector
    from app.models.profile import Profile
    from app.models.conversation import Conversation, ConversationMessage
    from app.models.test_repository import TestRepositoryItem
    from app.models.mcp_server import MCPServer
    
    Base.metadata.create_all(bind=engine)
    
    # Migrations: add columns that may not exist in older databases
    _run_migrations()


def _run_migrations():
    """Run simple schema migrations for new columns."""
    import sqlalchemy
    
    db = SessionLocal()
    try:
        # Check if media_type column exists in rag_files
        try:
            db.execute(sqlalchemy.text("SELECT media_type FROM rag_files LIMIT 1"))
        except Exception:
            try:
                db.execute(sqlalchemy.text("ALTER TABLE rag_files ADD COLUMN media_type VARCHAR(50)"))
                db.commit()
                print("[DB Migration] Added media_type column to rag_files")
            except Exception as e:
                db.rollback()

        # Check if mcp_server_id column exists in agents
        try:
            db.execute(sqlalchemy.text("SELECT mcp_server_id FROM agents LIMIT 1"))
        except Exception:
            try:
                db.execute(sqlalchemy.text("ALTER TABLE agents ADD COLUMN mcp_server_id INTEGER"))
                db.commit()
                print("[DB Migration] Added mcp_server_id column to agents")
            except Exception as e:
                db.rollback()

        # Check if password_hash column exists in users
        try:
            db.execute(sqlalchemy.text("SELECT password_hash FROM users LIMIT 1"))
        except Exception:
            try:
                db.execute(sqlalchemy.text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
                db.commit()
                print("[DB Migration] Added password_hash column to users")
            except Exception as e:
                db.rollback()
    finally:
        db.close()


# Pre-defined AI Engines to seed (updated January 2026)
ENGINES_TO_SEED = [
    # Anthropic Models
    {
        "provider": "Anthropic",
        "model_id": "claude-opus-4-5",
        "display_name": "Claude Opus 4.5",
        "description": "Peak intelligence, complex reasoning, mission-critical applications.",
        "input_cost": 5.00,
        "output_cost": 25.00
    },
    {
        "provider": "Anthropic",
        "model_id": "claude-sonnet-4-5",
        "display_name": "Claude Sonnet 4.5",
        "description": "Balanced performance, intelligent agents, advanced code generation.",
        "input_cost": 3.00,
        "output_cost": 15.00
    },
    {
        "provider": "Anthropic",
        "model_id": "claude-haiku-4-5",
        "display_name": "Claude Haiku 4.5",
        "description": "Speed-optimized tasks, high-volume processing, cost efficiency.",
        "input_cost": 1.00,
        "output_cost": 5.00
    },
    # OpenAI Models
    {
        "provider": "OpenAI",
        "model_id": "gpt-5",
        "display_name": "GPT-5",
        "description": "Top-tier general model with advanced reasoning capabilities.",
        "input_cost": 1.25,
        "output_cost": 10.00
    },
    {
        "provider": "OpenAI",
        "model_id": "gpt-5-mini",
        "display_name": "GPT-5 Mini",
        "description": "Faster, cheaper version of GPT-5 for efficient processing.",
        "input_cost": 0.25,
        "output_cost": 2.00
    },
    {
        "provider": "OpenAI",
        "model_id": "gpt-5-nano",
        "display_name": "GPT-5 Nano",
        "description": "Smallest model, optimized for simple tasks and low latency.",
        "input_cost": 0.05,
        "output_cost": 0.40
    },
    {
        "provider": "OpenAI",
        "model_id": "gpt-4o-vision",
        "display_name": "GPT-4o (Vision)",
        "description": "High visual/multi-modal capability for image understanding.",
        "input_cost": 5.00,
        "output_cost": 20.00
    },
    {
        "provider": "OpenAI",
        "model_id": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "description": "Lite version of GPT-4o for cost-effective multimodal tasks.",
        "input_cost": 0.60,
        "output_cost": 2.40
    },
    # Google Models
    {
        "provider": "Google",
        "model_id": "gemini-3-flash",
        "display_name": "Gemini 3 Flash",
        "description": "Fastest and highly capable for versatile applications, supports multimodal inputs.",
        "input_cost": 0.50,
        "output_cost": 3.00
    },
    {
        "provider": "Google",
        "model_id": "gemini-3-pro",
        "display_name": "Gemini 3 Pro",
        "description": "High-capability model for complex reasoning and coding, with large context window.",
        "input_cost": 2.00,
        "output_cost": 12.00
    },
    {
        "provider": "Google",
        "model_id": "gemini-2-5-flash",
        "display_name": "Gemini 2.5 Flash",
        "description": "Cost-effective, general-purpose model with good balance of intelligence and latency.",
        "input_cost": 0.15,
        "output_cost": 0.60
    },
    {
        "provider": "Google",
        "model_id": "gemini-2-5-pro",
        "display_name": "Gemini 2.5 Pro",
        "description": "Strong reasoning model with 1M token context window for complex tasks.",
        "input_cost": 1.25,
        "output_cost": 10.00
    },
    # xAI Models
    {
        "provider": "xAI",
        "model_id": "grok-4-1-fast",
        "display_name": "Grok 4.1 Fast",
        "description": "General chat, vision, reasoning, web search, audio input support.",
        "input_cost": 0.20,
        "output_cost": 0.50
    },
    {
        "provider": "xAI",
        "model_id": "grok-4-latest",
        "display_name": "Grok 4 (Latest)",
        "description": "General chat with web search capabilities.",
        "input_cost": 3.00,
        "output_cost": 15.00
    },
    {
        "provider": "xAI",
        "model_id": "grok-code-fast-1",
        "display_name": "Grok Code Fast",
        "description": "Agentic coding, code generation, completion, and debugging.",
        "input_cost": 0.20,
        "output_cost": 1.50
    },
    # Xiaomi MiMo Models
    {
        "provider": "MiMo",
        "model_id": "mimo-v2.5-pro",
        "display_name": "MiMo V2.5 Pro",
        "description": "Xiaomi flagship model. Top agentic capabilities, complex software engineering, 1M context window.",
        "input_cost": 0.435,
        "output_cost": 0.87
    },
    {
        "provider": "MiMo",
        "model_id": "mimo-v2.5",
        "display_name": "MiMo V2.5",
        "description": "Native omnimodal model with Pro-level agentic performance at lower cost.",
        "input_cost": 0.20,
        "output_cost": 0.40
    }
]


def seed_ai_engines():
    """
    Pre-populate the AI_Engines table with default models.
    Updates existing engines and adds new ones.
    """
    from app.models.ai_engine import AIEngine
    
    # Initialize database tables first
    init_db()
    
    db = SessionLocal()
    try:
        added_count = 0
        updated_count = 0
        
        for engine_data in ENGINES_TO_SEED:
            # Check if engine already exists by model_id
            existing = db.query(AIEngine).filter(
                AIEngine.model_id == engine_data["model_id"]
            ).first()
            
            if existing:
                # Update existing engine with new data (preserve API key)
                existing.provider = engine_data["provider"]
                existing.display_name = engine_data["display_name"]
                existing.description = engine_data["description"]
                existing.input_cost = engine_data["input_cost"]
                existing.output_cost = engine_data["output_cost"]
                updated_count += 1
            else:
                # Add new engine
                engine = AIEngine(**engine_data)
                db.add(engine)
                added_count += 1
        
        db.commit()
        return {"added": added_count, "updated": updated_count}
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def clear_old_engines():
    """
    Remove old engines that are no longer in the seed list.
    Only removes engines without API keys configured.
    """
    from app.models.ai_engine import AIEngine
    
    current_model_ids = [e["model_id"] for e in ENGINES_TO_SEED]
    
    db = SessionLocal()
    try:
        # Find engines not in current list and without API keys
        old_engines = db.query(AIEngine).filter(
            ~AIEngine.model_id.in_(current_model_ids),
            AIEngine.api_key_encrypted.is_(None)
        ).all()
        
        removed_count = 0
        for engine in old_engines:
            db.delete(engine)
            removed_count += 1
        
        db.commit()
        return removed_count
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_all_engines():
    """Get all AI engines from the database."""
    from app.models.ai_engine import AIEngine
    
    db = SessionLocal()
    try:
        return db.query(AIEngine).all()
    finally:
        db.close()


# Default applications to seed
DEFAULT_APPLICATIONS = [
    {
        "name": "AegisAI",
        "description": "Default Aegis AI application",
        "is_default": True
    },
    {
        "name": "CustomerSupport",
        "description": "Customer support chat application",
        "is_default": False
    },
    {
        "name": "InternalAssistant",
        "description": "Internal employee assistant",
        "is_default": False
    }
]


def seed_applications():
    """
    Pre-populate the Applications table with default application names.
    """
    from app.models.application import Application
    
    db = SessionLocal()
    try:
        added_count = 0
        
        for app_data in DEFAULT_APPLICATIONS:
            # Check if application already exists by name
            existing = db.query(Application).filter(
                Application.name == app_data["name"]
            ).first()
            
            if not existing:
                application = Application(**app_data)
                db.add(application)
                added_count += 1
        
        db.commit()
        return {"added": added_count}
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def seed_test_repository():
    """
    Pre-populate the Test Repository with AIDR policy testing samples.
    """
    from app.services.test_repository_service import seed_test_repository as seed_tr
    return seed_tr()


def seed_mcp_servers():
    """
    Pre-populate MCP Server configurations.
    """
    from app.services.mcp_server_service import seed_default_mcp_server
    return seed_default_mcp_server()
