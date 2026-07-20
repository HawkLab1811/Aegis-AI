"""
Aegis AI - Secure AI Gateway
FastAPI Backend Server

Port: 15000
"""

import os
import sys
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt

from app.core.config import load_config
from app.core.database import init_db, SessionLocal, seed_ai_engines, seed_applications
from app.services.user_service import UserService
from app.services.agent_service import AgentService
from app.services.ai_engine_service import AIEngineService
from app.services.rag_service import RAGService, RAG_STORAGE_BASE
from app.services.application_service import ApplicationService
from app.services.aidr_collector_service import AIDRCollectorService
from app.services.profile_service import ProfileService
from app.services.security import SecurityService, ExtraInfo, AIGuardClient
from app.models.agent import Agent
from app.models.user import User
from app.models.ai_engine import AIEngine
from app.models.rag import RAG, RAGFile
from app.models.application import Application
from app.models.aidr_collector import AIDRCollector
from app.models.profile import Profile
from app.models.conversation import Conversation, ConversationMessage as ConversationMessageModel
from app.services.conversation_service import ConversationService
from app.services.test_repository_service import TestRepositoryService
from app.models.test_repository import TestRepositoryItem
from app.models.mcp_server import MCPServer
from app.services.mcp_server_service import MCPServerService, MCP_TOOL_DESCRIPTIONS

# Initialize database
init_db()
seed_ai_engines()
seed_applications()
from app.core.database import seed_test_repository, seed_mcp_servers
seed_test_repository()
seed_mcp_servers()

# Initialize MCP workspace with sample files
from app.services.mcp_server_service import init_mcp_workspace
init_mcp_workspace()

# Load config
config = load_config()

# JWT Configuration
SECRET_KEY = config.get("ENCRYPTION_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# FastAPI app
app = FastAPI(
    title="Aegis AI",
    description="Secure AI Gateway with CrowdStrike AIDR Protection",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)


# ============================================================
# Pydantic Models
# ============================================================
class LoginRequest(BaseModel):
    password: str
    email: Optional[str] = "admin@aegis.ai"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_email: str


class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    rag_id: Optional[int] = None
    mcp_server_id: Optional[int] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    rag_id: Optional[int] = None
    mcp_server_id: Optional[int] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    system_prompt: Optional[str]
    rag_id: Optional[int]
    mcp_server_id: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True


# RAG Models
class RAGCreate(BaseModel):
    name: str
    description: Optional[str] = None


class RAGUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RAGResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class RAGFileResponse(BaseModel):
    id: int
    rag_id: int
    filename: str
    file_size: int
    file_type: Optional[str]
    media_type: Optional[str] = None
    is_processed: bool

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    is_admin: bool = False


class UserUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True


class EngineUpdate(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    is_active: Optional[bool] = None


class EngineResponse(BaseModel):
    id: int
    name: str
    provider: str
    model_id: str
    display_name: str
    description: Optional[str]
    input_cost: float
    output_cost: float
    base_url: Optional[str]
    is_active: bool
    has_api_key: bool

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    content: str
    agent_id: Optional[int] = None
    user_id: Optional[int] = None
    engine_id: Optional[int] = None
    app_name: Optional[str] = None  # Application name to send to AIDR
    security_enabled: bool = True  # AIDR protection toggle (default: enabled)
    collector_id: Optional[int] = None  # AIDR Collector to use (None = use .env defaults)
    conversation_id: Optional[int] = None  # Existing conversation to continue


class ChatContextInfo(BaseModel):
    """Context metadata returned with chat responses."""
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    engine_id: Optional[int] = None
    engine_name: Optional[str] = None
    app_name: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    blocked: bool = False
    violation_reason: Optional[str] = None
    context: Optional[ChatContextInfo] = None  # Context metadata for UI
    conversation_id: Optional[int] = None  # Conversation ID for tracking


# Application Models
class ApplicationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_default: bool = False


class ApplicationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class ApplicationResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    is_default: bool

    class Config:
        from_attributes = True


# AIDR Collector Models
class AIDRCollectorCreate(BaseModel):
    name: str
    description: Optional[str] = None
    token: str
    url: str = "https://api.crowdstrike.com/aidr/aiguard"
    is_default: bool = False


class AIDRCollectorUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    token: Optional[str] = None
    url: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class AIDRCollectorResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    url: str
    is_active: bool
    is_default: bool
    has_token: bool = True  # Always true if exists, token is masked

    class Config:
        from_attributes = True


# Profile Models
class ProfileCreate(BaseModel):
    name: str
    description: Optional[str] = None
    agent_id: Optional[int] = None
    user_id: Optional[int] = None
    engine_id: Optional[int] = None
    collector_id: Optional[int] = None
    app_name: Optional[str] = None
    is_default: bool = False


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agent_id: Optional[int] = None
    user_id: Optional[int] = None
    engine_id: Optional[int] = None
    collector_id: Optional[int] = None
    app_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    # Flags to explicitly clear values (set to None)
    clear_agent: bool = False
    clear_user: bool = False
    clear_engine: bool = False
    clear_collector: bool = False
    clear_app: bool = False


class ProfileResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    agent_id: Optional[int]
    agent_name: Optional[str] = None
    user_id: Optional[int]
    user_email: Optional[str] = None
    engine_id: Optional[int]
    engine_name: Optional[str] = None
    collector_id: Optional[int]
    collector_name: Optional[str] = None
    app_name: Optional[str]
    is_active: bool
    is_default: bool

    class Config:
        from_attributes = True


# ============================================================
# Conversation Models
# ============================================================
class ConversationCreate(BaseModel):
    title: Optional[str] = "New Chat"
    agent_id: Optional[int] = None
    engine_id: Optional[int] = None
    collector_id: Optional[int] = None
    app_name: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    agent_id: Optional[int] = None
    engine_id: Optional[int] = None
    collector_id: Optional[int] = None
    app_name: Optional[str] = None
    is_active: Optional[bool] = None


class ConversationResponse(BaseModel):
    id: int
    title: str
    user_id: int
    agent_id: Optional[int]
    engine_id: Optional[int]
    collector_id: Optional[int]
    app_name: Optional[str]
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationMessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    blocked: bool
    violation_reason: Optional[str]
    security_enabled: bool
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# MCP Server Models
class MCPServerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    command: str = sys.executable
    args: Optional[list] = None
    env_vars: Optional[dict] = None
    proxy_enabled: bool = True
    proxy_token: Optional[str] = None
    proxy_url: Optional[str] = None
    is_default: bool = False


class MCPServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    command: Optional[str] = None
    args: Optional[list] = None
    env_vars: Optional[dict] = None
    proxy_enabled: Optional[bool] = None
    proxy_token: Optional[str] = None
    proxy_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class MCPServerResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    command: str
    args: Optional[str]
    env_vars: Optional[str]
    proxy_enabled: bool
    proxy_url: Optional[str]
    is_active: bool
    is_default: bool
    has_token: bool = False

    class Config:
        from_attributes = True


# ============================================================
# Authentication Helpers
# ============================================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ============================================================
# Authentication Endpoints
# ============================================================
@app.post("/api/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login with email and password (database-backed)."""
    email = request.email or "admin@aegis.ai"
    
    with UserService() as user_service:
        user = user_service.authenticate(email, request.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return TokenResponse(
        access_token=access_token,
        user_email=user.email
    )


@app.get("/api/me")
async def get_current_user(email: str = Depends(verify_token)):
    """Get current authenticated user"""
    with UserService() as user_service:
        user = user_service.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse.model_validate(user)


# ============================================================
# Setup Wizard Endpoints
# ============================================================
@app.get("/api/setup/status")
async def setup_status():
    """Check if initial setup is complete."""
    with UserService() as user_service:
        admin_ready = user_service.has_admin_with_password()
    
    with AIDRCollectorService() as svc:
        aidr_ready = len(svc.get_all()) > 0
    
    engine_ready = False
    with AIEngineService() as svc:
        engines = svc.list_engines(active_only=True)
        engine_ready = any(e.api_key_encrypted for e in engines)
    
    return {
        "setup_complete": admin_ready and aidr_ready and engine_ready,
        "steps": {
            "admin": admin_ready,
            "aidr": aidr_ready,
            "mcp": True,  # Optional, skip if not needed
            "engine": engine_ready
        }
    }


class SetupAdminRequest(BaseModel):
    password: str
    confirm_password: str


@app.post("/api/setup/admin")
async def setup_admin(request: SetupAdminRequest):
    """Step 1: Create admin password."""
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if request.password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    with UserService() as user_service:
        user = user_service.get_or_create_user(
            email="admin@aegis.ai",
            name="Administrator",
            is_admin=True
        )
        user_service.set_password(user.id, request.password)
    
    return {"status": "ok", "message": "Admin password set"}


class SetupAIDRRequest(BaseModel):
    name: str = "Default AIDR Collector"
    description: Optional[str] = "Default AIDR configuration for application-level security scanning"
    token: str
    url: str = "https://api.crowdstrike.com/aidr/aiguard"


@app.post("/api/setup/aidr")
async def setup_aidr(request: SetupAIDRRequest):
    """Step 2: Create default AIDR collector."""
    if not request.token:
        raise HTTPException(status_code=400, detail="AIDR Token is required")
    
    with AIDRCollectorService() as svc:
        existing = svc.get_by_name(request.name)
        if existing:
            svc.update(
                collector_id=existing.id,
                token=request.token,
                url=request.url,
                description=request.description
            )
        else:
            svc.create(
                name=request.name,
                description=request.description,
                token=request.token,
                url=request.url,
                is_default=True
            )
    
    return {"status": "ok", "message": "AIDR collector configured"}


class SetupMCPRequest(BaseModel):
    name: str = "Default MCP Proxy"
    description: Optional[str] = "Default MCP proxy configuration for tool security scanning"
    token: Optional[str] = None
    url: str = "https://api.crowdstrike.com/aidr/{SERVICE_NAME}"


@app.post("/api/setup/mcp")
async def setup_mcp(request: SetupMCPRequest):
    """Step 3: Configure default MCP proxy settings for ALL active servers."""
    with MCPServerService() as svc:
        servers = svc.get_all(active_only=True)
        for server in servers:
            kwargs = {"proxy_enabled": True, "proxy_url": request.url}
            if request.token:
                kwargs["proxy_token"] = request.token
            svc.update(server.id, **kwargs)
    
    return {"status": "ok", "message": f"MCP proxy configured for {len(servers)} server(s)"}


class SetupEngineRequest(BaseModel):
    engine_id: int
    api_key: str


@app.post("/api/setup/engine")
async def setup_engine(request: SetupEngineRequest):
    """Step 4: Set API key for selected AI engine."""
    if not request.api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    
    with AIEngineService() as svc:
        engine = svc.get_engine_by_id(request.engine_id)
        if not engine:
            raise HTTPException(status_code=404, detail="Engine not found")
        svc.set_api_key(request.engine_id, request.api_key)
    
    return {"status": "ok", "message": f"API key set for {engine.display_name}"}


@app.get("/api/setup/engines")
async def setup_engines():
    """List available engines for the setup wizard (no auth required)."""
    with AIEngineService() as svc:
        engines = svc.list_engines(active_only=True)
        return [
            {
                "id": e.id,
                "display_name": e.display_name,
                "provider": e.provider,
                "model_id": e.model_id,
                "description": e.description,
            }
            for e in engines
        ]


@app.post("/api/setup/complete")
async def setup_complete():
    """Mark setup as complete and return login token."""
    with UserService() as user_service:
        if not user_service.has_admin_with_password():
            raise HTTPException(status_code=400, detail="Admin password not set")
        
        user = user_service.get_user_by_email("admin@aegis.ai")
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
    
    return {
        "status": "ok",
        "message": "Setup complete",
        "access_token": access_token,
        "user_email": user.email
    }


# ============================================================
# Agent Endpoints
# ============================================================
@app.get("/api/agents", response_model=List[AgentResponse])
async def list_agents(email: str = Depends(verify_token)):
    """List all agents"""
    with AgentService() as service:
        agents = service.list_agents(active_only=False)
        return [AgentResponse.model_validate(a) for a in agents]


@app.post("/api/agents", response_model=AgentResponse)
async def create_agent(agent: AgentCreate, email: str = Depends(verify_token)):
    """Create a new agent"""
    with AgentService() as service:
        try:
            new_agent = service.create_agent(
                name=agent.name,
                description=agent.description,
                system_prompt=agent.system_prompt,
                rag_id=agent.rag_id,
                mcp_server_id=agent.mcp_server_id
            )
            return AgentResponse.model_validate(new_agent)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, email: str = Depends(verify_token)):
    """Get agent by ID"""
    with AgentService() as service:
        agent = service.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return AgentResponse.model_validate(agent)


@app.put("/api/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: int, agent: AgentUpdate, email: str = Depends(verify_token)):
    """Update agent"""
    with AgentService() as service:
        updated = service.update_agent(
            agent_id,
            name=agent.name,
            description=agent.description,
            system_prompt=agent.system_prompt,
            rag_id=agent.rag_id,
            mcp_server_id=agent.mcp_server_id,
            is_active=agent.is_active
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Agent not found")
        return AgentResponse.model_validate(updated)


@app.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: int, email: str = Depends(verify_token)):
    """Delete agent (soft delete)"""
    with AgentService() as service:
        if not service.delete_agent(agent_id):
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"message": "Agent deleted"}


# ============================================================
# User Endpoints
# ============================================================
@app.get("/api/users", response_model=List[UserResponse])
async def list_users(email: str = Depends(verify_token)):
    """List all users"""
    with UserService() as service:
        users = service.list_users(active_only=False)
        return [UserResponse.model_validate(u) for u in users]


@app.post("/api/users", response_model=UserResponse)
async def create_user(user: UserCreate, email: str = Depends(verify_token)):
    """Create a new user"""
    with UserService() as service:
        try:
            new_user = service.create_user(
                email=user.email,
                name=user.name,
                is_admin=user.is_admin
            )
            return UserResponse.model_validate(new_user)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, email: str = Depends(verify_token)):
    """Get user by ID"""
    with UserService() as service:
        user = service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse.model_validate(user)


@app.put("/api/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user: UserUpdate, email: str = Depends(verify_token)):
    """Update user"""
    with UserService() as service:
        updated = service.update_user(
            user_id,
            name=user.name,
            is_active=user.is_active,
            is_admin=user.is_admin
        )
        if not updated:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse.model_validate(updated)


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, email: str = Depends(verify_token)):
    """Delete user (soft delete)"""
    with UserService() as service:
        if not service.delete_user(user_id):
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User deleted"}


# ============================================================
# RAG Endpoints
# ============================================================
@app.get("/api/rags", response_model=List[RAGResponse])
async def list_rags(email: str = Depends(verify_token)):
    """List all RAG knowledge bases"""
    with RAGService() as service:
        rags = service.list_rags(active_only=False)
        return [RAGResponse.model_validate(r) for r in rags]


@app.post("/api/rags", response_model=RAGResponse)
async def create_rag(rag: RAGCreate, email: str = Depends(verify_token)):
    """Create a new RAG knowledge base"""
    with RAGService() as service:
        try:
            new_rag = service.create_rag(
                name=rag.name,
                description=rag.description
            )
            return RAGResponse.model_validate(new_rag)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/rags/{rag_id}", response_model=RAGResponse)
async def get_rag(rag_id: int, email: str = Depends(verify_token)):
    """Get RAG by ID"""
    with RAGService() as service:
        rag = service.get_rag_by_id(rag_id)
        if not rag:
            raise HTTPException(status_code=404, detail="RAG not found")
        return RAGResponse.model_validate(rag)


@app.put("/api/rags/{rag_id}", response_model=RAGResponse)
async def update_rag(rag_id: int, rag: RAGUpdate, email: str = Depends(verify_token)):
    """Update RAG"""
    with RAGService() as service:
        try:
            updated = service.update_rag(
                rag_id,
                name=rag.name,
                description=rag.description,
                is_active=rag.is_active
            )
            if not updated:
                raise HTTPException(status_code=404, detail="RAG not found")
            return RAGResponse.model_validate(updated)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/rags/{rag_id}")
async def delete_rag(rag_id: int, email: str = Depends(verify_token)):
    """Delete RAG (soft delete)"""
    with RAGService() as service:
        if not service.delete_rag(rag_id):
            raise HTTPException(status_code=404, detail="RAG not found")
        return {"message": "RAG deleted"}


@app.get("/api/rags/{rag_id}/files", response_model=List[RAGFileResponse])
async def list_rag_files(rag_id: int, email: str = Depends(verify_token)):
    """List files for a specific RAG"""
    with RAGService() as service:
        files = service.list_files_by_rag(rag_id)
        return [RAGFileResponse.model_validate(f) for f in files]


@app.post("/api/rags/{rag_id}/upload")
async def upload_rag_file_to_rag(
    rag_id: int,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload file to a specific RAG and vectorize it"""
    from app.services.rag import get_vector_store_service
    from app.services.rag.media_extractor import (
        IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, EXCEL_EXTENSIONS,
        CSV_EXTENSIONS, WORD_EXTENSIONS, PPT_EXTENSIONS
    )

    with RAGService() as service:
        # Verify RAG exists
        rag = service.get_rag_by_id(rag_id)
        if not rag:
            raise HTTPException(status_code=404, detail="RAG not found")

        # Get storage path for this RAG
        rag_dir = service.get_rag_storage_path(rag_id)

        # Save file
        file_path = rag_dir / file.filename
        content = await file.read()

        with open(file_path, "wb") as f:
            f.write(content)

        # Detect media type from extension
        suffix = Path(file.filename).suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            media_type = "image"
        elif suffix in VIDEO_EXTENSIONS:
            media_type = "video"
        elif suffix in EXCEL_EXTENSIONS:
            media_type = "excel"
        elif suffix in CSV_EXTENSIONS:
            media_type = "csv"
        elif suffix in WORD_EXTENSIONS:
            media_type = "docx"
        elif suffix in PPT_EXTENSIONS:
            media_type = "pptx"
        elif suffix == '.pdf':
            media_type = "pdf"
        else:
            media_type = "document"

        # Record file in database
        rag_file = service.add_file(
            rag_id=rag_id,
            filename=file.filename,
            file_path=str(file_path),
            file_size=len(content),
            file_type=file.content_type,
            media_type=media_type
        )

        # Vectorize the file for RAG retrieval
        try:
            vector_store = get_vector_store_service()
            chunks_added = vector_store.add_document(
                rag_id=rag_id,
                file_path=file_path,
                file_id=rag_file.id
            )

            # Mark file as processed
            if chunks_added > 0:
                service.mark_file_processed(rag_file.id)
                rag_file = service.get_file_by_id(rag_file.id)
        except Exception as e:
            print(f"Warning: Failed to vectorize file {file.filename}: {e}")

        return RAGFileResponse.model_validate(rag_file)


@app.delete("/api/rags/{rag_id}/files/{file_id}")
async def delete_rag_file(rag_id: int, file_id: int, email: str = Depends(verify_token)):
    """Delete a file from a RAG and its vectors"""
    from app.services.rag import get_vector_store_service
    
    with RAGService() as service:
        rag_file = service.get_file_by_id(file_id)
        if not rag_file or rag_file.rag_id != rag_id:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path_str = rag_file.file_path
        
        # Remove from vector store
        try:
            vector_store = get_vector_store_service()
            vector_store.remove_document(rag_id, file_path_str)
        except Exception as e:
            print(f"Warning: Failed to remove vectors for {file_path_str}: {e}")
        
        # Delete the actual file
        file_path = Path(file_path_str)
        if file_path.exists():
            file_path.unlink()
        
        # Delete from database
        service.delete_file(file_id)
        return {"message": "File deleted"}


# ============================================================
# Engine Endpoints
# ============================================================
@app.get("/api/engines", response_model=List[EngineResponse])
async def list_engines(email: str = Depends(verify_token)):
    """List all AI engines"""
    with AIEngineService() as service:
        engines = service.list_engines(active_only=False)
        result = []
        for e in engines:
            result.append(EngineResponse(
                id=e.id,
                name=e.display_name,
                provider=e.provider,
                model_id=e.model_id,
                display_name=e.display_name,
                description=e.description,
                input_cost=e.input_cost,
                output_cost=e.output_cost,
                base_url=e.base_url,
                is_active=e.is_active,
                has_api_key=e.api_key_encrypted is not None
            ))
        return result


@app.put("/api/engines/{engine_id}", response_model=EngineResponse)
async def update_engine(engine_id: int, engine: EngineUpdate, email: str = Depends(verify_token)):
    """Update engine (set API key, etc.)"""
    with AIEngineService() as service:
        # Update API key if provided
        if engine.api_key:
            service.set_api_key(engine_id, engine.api_key)
        
        # Update other fields
        updated = service.update_engine(
            engine_id,
            base_url=engine.base_url,
            is_active=engine.is_active
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Engine not found")
        
        return EngineResponse(
            id=updated.id,
            name=updated.display_name,
            provider=updated.provider,
            model_id=updated.model_id,
            display_name=updated.display_name,
            description=updated.description,
            input_cost=updated.input_cost,
            output_cost=updated.output_cost,
            base_url=updated.base_url,
            is_active=updated.is_active,
            has_api_key=updated.api_key_encrypted is not None
        )


# ============================================================
# Application Endpoints
# ============================================================
@app.get("/api/applications", response_model=List[ApplicationResponse])
async def list_applications(email: str = Depends(verify_token)):
    """List all application names"""
    db = SessionLocal()
    try:
        service = ApplicationService(db)
        apps = service.get_all(active_only=False)
        return [ApplicationResponse.model_validate(a) for a in apps]
    finally:
        db.close()


@app.post("/api/applications", response_model=ApplicationResponse)
async def create_application(app_data: ApplicationCreate, email: str = Depends(verify_token)):
    """Create a new application name"""
    db = SessionLocal()
    try:
        service = ApplicationService(db)
        # Check if name already exists
        existing = service.get_by_name(app_data.name)
        if existing:
            raise HTTPException(status_code=400, detail="Application name already exists")
        
        new_app = service.create(
            name=app_data.name,
            description=app_data.description,
            is_default=app_data.is_default
        )
        return ApplicationResponse.model_validate(new_app)
    finally:
        db.close()


@app.get("/api/applications/{app_id}", response_model=ApplicationResponse)
async def get_application(app_id: int, email: str = Depends(verify_token)):
    """Get application by ID"""
    db = SessionLocal()
    try:
        service = ApplicationService(db)
        app = service.get_by_id(app_id)
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        return ApplicationResponse.model_validate(app)
    finally:
        db.close()


@app.put("/api/applications/{app_id}", response_model=ApplicationResponse)
async def update_application(app_id: int, app_data: ApplicationUpdate, email: str = Depends(verify_token)):
    """Update application"""
    db = SessionLocal()
    try:
        service = ApplicationService(db)
        
        # Check if new name already exists (if changing name)
        if app_data.name:
            existing = service.get_by_name(app_data.name)
            if existing and existing.id != app_id:
                raise HTTPException(status_code=400, detail="Application name already exists")
        
        updated = service.update(
            app_id,
            name=app_data.name,
            description=app_data.description,
            is_active=app_data.is_active,
            is_default=app_data.is_default
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Application not found")
        return ApplicationResponse.model_validate(updated)
    finally:
        db.close()


@app.delete("/api/applications/{app_id}")
async def delete_application(app_id: int, email: str = Depends(verify_token)):
    """Delete application (soft delete)"""
    db = SessionLocal()
    try:
        service = ApplicationService(db)
        if not service.delete(app_id):
            raise HTTPException(status_code=404, detail="Application not found")
        return {"message": "Application deleted"}
    finally:
        db.close()


# ============================================================
# AIDR Collector Endpoints
# ============================================================
@app.get("/api/aidr-collectors", response_model=List[AIDRCollectorResponse])
async def list_aidr_collectors(active_only: bool = False, email: str = Depends(verify_token)):
    """List all AIDR collectors"""
    with AIDRCollectorService() as service:
        collectors = service.get_all(active_only=active_only)
        return [
            AIDRCollectorResponse(
                id=c.id,
                name=c.name,
                description=c.description,
                url=c.url,
                is_active=c.is_active,
                is_default=c.is_default,
                has_token=bool(c.token)
            )
            for c in collectors
        ]


@app.post("/api/aidr-collectors", response_model=AIDRCollectorResponse)
async def create_aidr_collector(collector: AIDRCollectorCreate, email: str = Depends(verify_token)):
    """Create a new AIDR collector"""
    with AIDRCollectorService() as service:
        # Check if name already exists
        existing = service.get_by_name(collector.name)
        if existing:
            raise HTTPException(status_code=400, detail="Collector with this name already exists")
        
        new_collector = service.create(
            name=collector.name,
            description=collector.description,
            token=collector.token,
            url=collector.url,
            is_default=collector.is_default
        )
        
        return AIDRCollectorResponse(
            id=new_collector.id,
            name=new_collector.name,
            description=new_collector.description,
            url=new_collector.url,
            is_active=new_collector.is_active,
            is_default=new_collector.is_default,
            has_token=bool(new_collector.token)
        )


@app.get("/api/aidr-collectors/{collector_id}", response_model=AIDRCollectorResponse)
async def get_aidr_collector(collector_id: int, email: str = Depends(verify_token)):
    """Get AIDR collector by ID"""
    with AIDRCollectorService() as service:
        collector = service.get_by_id(collector_id)
        if not collector:
            raise HTTPException(status_code=404, detail="Collector not found")
        
        return AIDRCollectorResponse(
            id=collector.id,
            name=collector.name,
            description=collector.description,
            url=collector.url,
            is_active=collector.is_active,
            is_default=collector.is_default,
            has_token=bool(collector.token)
        )


@app.put("/api/aidr-collectors/{collector_id}", response_model=AIDRCollectorResponse)
async def update_aidr_collector(collector_id: int, update: AIDRCollectorUpdate, email: str = Depends(verify_token)):
    """Update an AIDR collector"""
    with AIDRCollectorService() as service:
        # Check name uniqueness if updating name
        if update.name:
            existing = service.get_by_name(update.name)
            if existing and existing.id != collector_id:
                raise HTTPException(status_code=400, detail="Collector with this name already exists")
        
        updated = service.update(
            collector_id=collector_id,
            name=update.name,
            description=update.description,
            token=update.token,
            url=update.url,
            is_active=update.is_active,
            is_default=update.is_default
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Collector not found")
        
        return AIDRCollectorResponse(
            id=updated.id,
            name=updated.name,
            description=updated.description,
            url=updated.url,
            is_active=updated.is_active,
            is_default=updated.is_default,
            has_token=bool(updated.token)
        )


@app.delete("/api/aidr-collectors/{collector_id}")
async def delete_aidr_collector(collector_id: int, email: str = Depends(verify_token)):
    """Delete AIDR collector (soft delete)"""
    with AIDRCollectorService() as service:
        if not service.delete(collector_id):
            raise HTTPException(status_code=404, detail="Collector not found")
        return {"message": "Collector deleted"}


@app.post("/api/aidr-collectors/{collector_id}/set-default")
async def set_default_aidr_collector(collector_id: int, email: str = Depends(verify_token)):
    """Set an AIDR collector as the default"""
    with AIDRCollectorService() as service:
        updated = service.update(collector_id=collector_id, is_default=True)
        if not updated:
            raise HTTPException(status_code=404, detail="Collector not found")
        return {"message": "Collector set as default"}


# ============================================================
# Profile Endpoints
# ============================================================
@app.get("/api/profiles", response_model=List[ProfileResponse])
async def list_profiles(active_only: bool = False, email: str = Depends(verify_token)):
    """List all profiles with resolved entity names"""
    with ProfileService() as service:
        profiles = service.get_all(active_only=active_only)
        result = []
        for p in profiles:
            details = service.get_profile_with_details(p.id)
            if details:
                result.append(ProfileResponse(**details))
        return result


@app.post("/api/profiles", response_model=ProfileResponse)
async def create_profile(profile: ProfileCreate, email: str = Depends(verify_token)):
    """Create a new profile"""
    with ProfileService() as service:
        # Check if name already exists
        existing = service.get_by_name(profile.name)
        if existing:
            raise HTTPException(status_code=400, detail="Profile with this name already exists")
        
        new_profile = service.create(
            name=profile.name,
            description=profile.description,
            agent_id=profile.agent_id,
            user_id=profile.user_id,
            engine_id=profile.engine_id,
            collector_id=profile.collector_id,
            app_name=profile.app_name,
            is_default=profile.is_default
        )
        
        details = service.get_profile_with_details(new_profile.id)
        return ProfileResponse(**details)


@app.get("/api/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: int, email: str = Depends(verify_token)):
    """Get profile by ID with resolved entity names"""
    with ProfileService() as service:
        details = service.get_profile_with_details(profile_id)
        if not details:
            raise HTTPException(status_code=404, detail="Profile not found")
        return ProfileResponse(**details)


@app.put("/api/profiles/{profile_id}", response_model=ProfileResponse)
async def update_profile(profile_id: int, update: ProfileUpdate, email: str = Depends(verify_token)):
    """Update a profile"""
    with ProfileService() as service:
        # Check name uniqueness if updating name
        if update.name:
            existing = service.get_by_name(update.name)
            if existing and existing.id != profile_id:
                raise HTTPException(status_code=400, detail="Profile with this name already exists")
        
        updated = service.update(
            profile_id=profile_id,
            name=update.name,
            description=update.description,
            agent_id=update.agent_id,
            user_id=update.user_id,
            engine_id=update.engine_id,
            collector_id=update.collector_id,
            app_name=update.app_name,
            is_active=update.is_active,
            is_default=update.is_default,
            clear_agent=update.clear_agent,
            clear_user=update.clear_user,
            clear_engine=update.clear_engine,
            clear_collector=update.clear_collector,
            clear_app=update.clear_app
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        details = service.get_profile_with_details(updated.id)
        return ProfileResponse(**details)


@app.delete("/api/profiles/{profile_id}")
async def delete_profile(profile_id: int, email: str = Depends(verify_token)):
    """Delete profile (soft delete)"""
    with ProfileService() as service:
        if not service.delete(profile_id):
            raise HTTPException(status_code=404, detail="Profile not found")
        return {"message": "Profile deleted"}


@app.post("/api/profiles/{profile_id}/set-default")
async def set_default_profile(profile_id: int, email: str = Depends(verify_token)):
    """Set a profile as the default"""
    with ProfileService() as service:
        updated = service.update(profile_id=profile_id, is_default=True)
        if not updated:
            raise HTTPException(status_code=404, detail="Profile not found")
        return {"message": "Profile set as default"}


# ============================================================
# Conversation Endpoints
# ============================================================
@app.get("/api/conversations", response_model=List[ConversationResponse])
async def list_conversations(email: str = Depends(verify_token)):
    """List all conversations for the current user."""
    with UserService() as user_service:
        user = user_service.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    with ConversationService() as conv_service:
        conversations = conv_service.list_conversations(user.id)
        result = []
        for conv in conversations:
            messages = conv_service.get_messages(conv.id)
            result.append(ConversationResponse(
                id=conv.id,
                title=conv.title,
                user_id=conv.user_id,
                agent_id=conv.agent_id,
                engine_id=conv.engine_id,
                collector_id=conv.collector_id,
                app_name=conv.app_name,
                is_active=conv.is_active,
                created_at=str(conv.created_at) if conv.created_at else None,
                updated_at=str(conv.updated_at) if conv.updated_at else None,
                message_count=len(messages)
            ))
        return result


@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation(conv_data: ConversationCreate, email: str = Depends(verify_token)):
    """Create a new conversation."""
    with UserService() as user_service:
        user = user_service.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    with ConversationService() as conv_service:
        conv = conv_service.create_conversation(
            user_id=user.id,
            title=conv_data.title or "New Chat",
            agent_id=conv_data.agent_id,
            engine_id=conv_data.engine_id,
            collector_id=conv_data.collector_id,
            app_name=conv_data.app_name
        )
        return ConversationResponse(
            id=conv.id,
            title=conv.title,
            user_id=conv.user_id,
            agent_id=conv.agent_id,
            engine_id=conv.engine_id,
            collector_id=conv.collector_id,
            app_name=conv.app_name,
            is_active=conv.is_active,
            created_at=str(conv.created_at) if conv.created_at else None,
            updated_at=str(conv.updated_at) if conv.updated_at else None,
            message_count=0
        )


@app.get("/api/conversations/{conv_id}", response_model=ConversationResponse)
async def get_conversation(conv_id: int, email: str = Depends(verify_token)):
    """Get a specific conversation."""
    with UserService() as user_service:
        user = user_service.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    with ConversationService() as conv_service:
        conv = conv_service.get_conversation(conv_id)
        if not conv or conv.user_id != user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        messages = conv_service.get_messages(conv_id)
        return ConversationResponse(
            id=conv.id,
            title=conv.title,
            user_id=conv.user_id,
            agent_id=conv.agent_id,
            engine_id=conv.engine_id,
            collector_id=conv.collector_id,
            app_name=conv.app_name,
            is_active=conv.is_active,
            created_at=str(conv.created_at) if conv.created_at else None,
            updated_at=str(conv.updated_at) if conv.updated_at else None,
            message_count=len(messages)
        )


@app.get("/api/conversations/{conv_id}/messages", response_model=List[ConversationMessageResponse])
async def get_conversation_messages(conv_id: int, email: str = Depends(verify_token)):
    """Get all messages in a conversation."""
    with UserService() as user_service:
        user = user_service.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    with ConversationService() as conv_service:
        conv = conv_service.get_conversation(conv_id)
        if not conv or conv.user_id != user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        messages = conv_service.get_messages(conv_id)
        return [ConversationMessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            blocked=m.blocked,
            violation_reason=m.violation_reason,
            security_enabled=m.security_enabled,
            created_at=str(m.created_at) if m.created_at else None
        ) for m in messages]


@app.put("/api/conversations/{conv_id}", response_model=ConversationResponse)
async def update_conversation(conv_id: int, update: ConversationUpdate, email: str = Depends(verify_token)):
    """Update a conversation."""
    with UserService() as user_service:
        user = user_service.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    with ConversationService() as conv_service:
        conv = conv_service.get_conversation(conv_id)
        if not conv or conv.user_id != user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        updated = conv_service.update_conversation(
            conv_id,
            title=update.title,
            agent_id=update.agent_id,
            engine_id=update.engine_id,
            collector_id=update.collector_id,
            app_name=update.app_name,
            is_active=update.is_active
        )
        messages = conv_service.get_messages(conv_id)
        return ConversationResponse(
            id=updated.id,
            title=updated.title,
            user_id=updated.user_id,
            agent_id=updated.agent_id,
            engine_id=updated.engine_id,
            collector_id=updated.collector_id,
            app_name=updated.app_name,
            is_active=updated.is_active,
            created_at=str(updated.created_at) if updated.created_at else None,
            updated_at=str(updated.updated_at) if updated.updated_at else None,
            message_count=len(messages)
        )


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: int, email: str = Depends(verify_token)):
    """Delete a conversation and all its messages."""
    with UserService() as user_service:
        user = user_service.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    with ConversationService() as conv_service:
        conv = conv_service.get_conversation(conv_id)
        if not conv or conv.user_id != user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conv_service.delete_conversation(conv_id)
        return {"message": "Conversation deleted"}


# ============================================================
# Test Repository Endpoints
# ============================================================
@app.get("/api/test-repository")
async def list_test_repository(
    category: Optional[str] = None,
    email: str = Depends(verify_token)
):
    """List all test repository items, optionally filtered by category."""
    with TestRepositoryService() as service:
        items = service.get_all(category=category)
        return [{
            "id": item.id,
            "category": item.category,
            "subcategory": item.subcategory,
            "name": item.name,
            "description": item.description,
            "prompt_text": item.prompt_text,
            "severity": item.severity,
            "is_active": item.is_active
        } for item in items]


@app.get("/api/test-repository/categories")
async def list_test_categories(email: str = Depends(verify_token)):
    """List all test repository categories."""
    with TestRepositoryService() as service:
        categories = service.get_categories()
        result = []
        for cat in categories:
            items = service.get_all(category=cat)
            result.append({
                "category": cat,
                "count": len(items),
                "subcategories": list(set(i.subcategory for i in items if i.subcategory))
            })
        return result


@app.get("/api/test-repository/random/{category}")
async def get_random_test_prompt(category: str, email: str = Depends(verify_token)):
    """Get a random test prompt from a specific category."""
    with TestRepositoryService() as service:
        item = service.get_random_by_category(category)
        if not item:
            raise HTTPException(status_code=404, detail=f"No items found in category: {category}")
        return {
            "id": item.id,
            "category": item.category,
            "subcategory": item.subcategory,
            "name": item.name,
            "description": item.description,
            "prompt_text": item.prompt_text,
            "severity": item.severity
        }


@app.post("/api/test-repository")
async def create_test_item(
    data: dict,
    email: str = Depends(verify_token)
):
    """Add a new test repository item."""
    with TestRepositoryService() as service:
        item = service.create(
            category=data.get("category", "custom"),
            name=data.get("name", "Custom Test"),
            prompt_text=data.get("prompt_text", ""),
            subcategory=data.get("subcategory"),
            description=data.get("description"),
            severity=data.get("severity", "medium")
        )
        return {
            "id": item.id,
            "category": item.category,
            "name": item.name,
            "prompt_text": item.prompt_text,
            "severity": item.severity
        }


@app.delete("/api/test-repository/{item_id}")
async def delete_test_item(item_id: int, email: str = Depends(verify_token)):
    """Delete a test repository item."""
    with TestRepositoryService() as service:
        if not service.delete(item_id):
            raise HTTPException(status_code=404, detail="Item not found")
        return {"message": "Item deleted"}


@app.put("/api/test-repository/{item_id}")
async def update_test_item(item_id: int, data: dict, email: str = Depends(verify_token)):
    """Update a test repository item."""
    with TestRepositoryService() as service:
        item = service.update(item_id, **data)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return {
            "id": item.id,
            "category": item.category,
            "name": item.name,
            "prompt_text": item.prompt_text,
            "severity": item.severity
        }


# ============================================================
# MCP Server Endpoints
# ============================================================
@app.get("/api/mcp-servers", response_model=List[MCPServerResponse])
async def list_mcp_servers(email: str = Depends(verify_token)):
    """List all MCP server configurations."""
    with MCPServerService() as service:
        servers = service.get_all()
        return [MCPServerResponse(
            id=s.id, name=s.name, description=s.description,
            command=s.command, args=s.args, env_vars=s.env_vars,
            proxy_enabled=s.proxy_enabled, proxy_url=s.proxy_url,
            is_active=s.is_active, is_default=s.is_default,
            has_token=bool(s.proxy_token)
        ) for s in servers]


@app.post("/api/mcp-servers", response_model=MCPServerResponse)
async def create_mcp_server(data: MCPServerCreate, email: str = Depends(verify_token)):
    """Create a new MCP server configuration."""
    with MCPServerService() as service:
        existing = service.get_by_name(data.name)
        if existing:
            raise HTTPException(status_code=400, detail="MCP server with this name already exists")
        server = service.create(
            name=data.name, command=data.command, description=data.description,
            args=data.args, env_vars=data.env_vars,
            proxy_enabled=data.proxy_enabled, proxy_token=data.proxy_token,
            proxy_url=data.proxy_url, is_default=data.is_default
        )
        return MCPServerResponse(
            id=server.id, name=server.name, description=server.description,
            command=server.command, args=server.args, env_vars=server.env_vars,
            proxy_enabled=server.proxy_enabled, proxy_url=server.proxy_url,
            is_active=server.is_active, is_default=server.is_default,
            has_token=bool(server.proxy_token)
        )


@app.get("/api/mcp-servers/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(server_id: int, email: str = Depends(verify_token)):
    """Get MCP server by ID."""
    with MCPServerService() as service:
        server = service.get_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="MCP server not found")
        return MCPServerResponse(
            id=server.id, name=server.name, description=server.description,
            command=server.command, args=server.args, env_vars=server.env_vars,
            proxy_enabled=server.proxy_enabled, proxy_url=server.proxy_url,
            is_active=server.is_active, is_default=server.is_default,
            has_token=bool(server.proxy_token)
        )


@app.put("/api/mcp-servers/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(server_id: int, data: MCPServerUpdate, email: str = Depends(verify_token)):
    """Update an MCP server configuration."""
    with MCPServerService() as service:
        kwargs = {}
        for field in ['name', 'description', 'command', 'args', 'env_vars',
                       'proxy_enabled', 'proxy_token', 'proxy_url', 'is_active', 'is_default']:
            val = getattr(data, field, None)
            if val is not None:
                kwargs[field] = val
        updated = service.update(server_id, **kwargs)
        if not updated:
            raise HTTPException(status_code=404, detail="MCP server not found")
        return MCPServerResponse(
            id=updated.id, name=updated.name, description=updated.description,
            command=updated.command, args=updated.args, env_vars=updated.env_vars,
            proxy_enabled=updated.proxy_enabled, proxy_url=updated.proxy_url,
            is_active=updated.is_active, is_default=updated.is_default,
            has_token=bool(updated.proxy_token)
        )


@app.delete("/api/mcp-servers/{server_id}")
async def delete_mcp_server(server_id: int, email: str = Depends(verify_token)):
    """Delete an MCP server configuration."""
    with MCPServerService() as service:
        if not service.delete(server_id):
            raise HTTPException(status_code=404, detail="MCP server not found")
        return {"message": "MCP server deleted"}


@app.get("/api/mcp-servers/{server_id}/tools")
async def get_mcp_tools(server_id: int, email: str = Depends(verify_token)):
    """Get available MCP tools for a server."""
    with MCPServerService() as service:
        server = service.get_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="MCP server not found")
        return {"tools": MCP_TOOL_DESCRIPTIONS, "proxy_enabled": server.proxy_enabled}


@app.get("/api/mcp-servers/{server_id}/validate")
async def validate_mcp_server(server_id: int, email: str = Depends(verify_token)):
    """Pre-flight validation for MCP server configuration."""
    with MCPServerService() as service:
        config = service.get_server_config(server_id)
        if not config:
            raise HTTPException(status_code=404, detail="MCP server not found")

    from app.services.mcp_executor import get_mcp_executor
    executor = get_mcp_executor(config["name"], config)
    return executor.validate()


# ============================================================
# Chat Endpoint - Full Orchestration
# Flow: Input -> AIDR Input Scan -> RAG -> LLM -> AIDR Output Scan -> Display
# ============================================================
@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, email: str = Depends(verify_token)):
    """
    Process chat message through the full secure AI pipeline.
    
    STATELESS DESIGN: Every request fetches fresh context from the database:
    - Agent's system prompt and RAG binding
    - Engine's API key and model details
    - User's identity for AIDR scanning
    
    CONVERSATION SUPPORT: If conversation_id is provided, loads message history
    and appends new messages. Otherwise, creates a new conversation.
    
    Flow:
    1. AIDR Input Scan - Check user input for security violations
    2. RAG Retrieval - Get relevant context from knowledge base (if agent has RAG)
    3. LLM Generation - Generate response using configured engine
    4. AIDR Output Scan - Check LLM output for security violations
    5. Return response to user with context metadata
    """
    from app.services.llm.factory import get_provider_from_engine
    from app.services.rag import get_vector_store_service
    
    # ========================================
    # Step 0: Gather context (user, agent, engine) - FRESH FOR EACH REQUEST
    # ========================================
    
    # Initialize context tracking for response metadata
    agent_name = "Default Agent"
    engine_display_name = None
    
    # Get authenticated user (conversation owner)
    with UserService() as user_service:
        auth_user = user_service.get_user_by_email(email)
        if not auth_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user for AIDR scanning (may differ from auth user if dropdown selected)
        if message.user_id:
            user = user_service.get_user_by_id(message.user_id)
        else:
            user = auth_user
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    # Get engine info - FRESH FETCH
    engine = None
    engine_name = "OpenAI"
    model_name = "gpt-5"
    
    if message.engine_id:
        with AIEngineService() as engine_service:
            engine = engine_service.get_engine_by_id(message.engine_id)
            if engine:
                engine_name = engine.provider
                model_name = engine.model_id
                engine_display_name = engine.display_name
    
    # Get agent info - FRESH FETCH (includes system prompt, RAG linkage, and MCP tools)
    system_prompt = "You are a helpful AI assistant."
    rag_id = None
    mcp_server_id = None

    if message.agent_id:
        with AgentService() as agent_service:
            agent = agent_service.get_agent_by_id(message.agent_id)
            if agent:
                agent_name = agent.name
                if agent.system_prompt:
                    system_prompt = agent.system_prompt
                rag_id = agent.rag_id
                mcp_server_id = agent.mcp_server_id

    # Inject MCP tool descriptions into system prompt if agent has an MCP server
    mcp_server_name = None
    mcp_config = None
    if mcp_server_id:
        with MCPServerService() as mcp_service:
            mcp_config = mcp_service.get_server_config(mcp_server_id)
            if mcp_config:
                mcp_server_name = mcp_config["name"]
                tools_desc = mcp_service.get_tools_description(mcp_server_id)
                proxy_status = "ENABLED (routed through CrowdStrike AIDR MCP proxy)" if mcp_config["proxy_enabled"] else "DISABLED (direct connection, no proxy scanning)"
                system_prompt += f"\n\n{tools_desc}\n\n**MCP Proxy Status:** {proxy_status}\n"
                print(f"[MCP] Agent '{agent_name}' bound to MCP server '{mcp_server_name}' (proxy: {proxy_status})")
    
    # Get application name (default to "AegisAI" if not specified)
    app_name = message.app_name or "AegisAI"
    
    # Get AIDR Collector configuration - FRESH FETCH
    collector_name = "Default (.env)"
    aidr_token = None
    aidr_url = None
    
    if message.collector_id:
        with AIDRCollectorService() as collector_service:
            collector_config = collector_service.get_collector_config(message.collector_id)
            if collector_config:
                collector_name = collector_config["name"]
                aidr_token = collector_config["token"]
                aidr_url = collector_config["url"]
    
    # ========================================
    # Step 0b: Handle Conversation
    # ========================================
    conversation_id = message.conversation_id
    chat_history = []
    
    with ConversationService() as conv_service:
        if conversation_id:
            # Verify conversation exists and belongs to user
            conv = conv_service.get_conversation(conversation_id)
            if not conv or conv.user_id != auth_user.id:
                # Create new conversation if invalid ID
                conv = conv_service.create_conversation(
                    user_id=auth_user.id,
                    title=message.content[:50] + ("..." if len(message.content) > 50 else ""),
                    agent_id=message.agent_id,
                    engine_id=message.engine_id,
                    collector_id=message.collector_id,
                    app_name=app_name
                )
                conversation_id = conv.id
            else:
                # Load existing history for LLM context
                chat_history = conv_service.get_history_for_llm(conversation_id)
                # Update conversation context if changed
                conv_service.update_conversation(
                    conversation_id,
                    agent_id=message.agent_id,
                    engine_id=message.engine_id,
                    collector_id=message.collector_id,
                    app_name=app_name
                )
        else:
            # Create new conversation
            conv = conv_service.create_conversation(
                user_id=auth_user.id,
                title=message.content[:50] + ("..." if len(message.content) > 50 else ""),
                agent_id=message.agent_id,
                engine_id=message.engine_id,
                collector_id=message.collector_id,
                app_name=app_name
            )
            conversation_id = conv.id
        
        # Save user message to conversation
        conv_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=message.content,
            security_enabled=message.security_enabled
        )
    
    # Build context info for response
    context_info = ChatContextInfo(
        agent_id=message.agent_id,
        agent_name=agent_name,
        user_id=user.id,
        user_email=user.email,
        engine_id=message.engine_id,
        engine_name=engine_display_name,
        app_name=app_name
    )
    
    # ========================================
    # LOG: Dynamic context for this request
    # ========================================
    print(f"[CHAT] === New Chat Request ===")
    print(f"[CHAT] Conversation ID: {conversation_id}")
    print(f"[CHAT] Agent: {agent_name} (ID: {message.agent_id})")
    print(f"[CHAT] Engine: {engine_display_name or 'Not configured'} (Provider: {engine_name}, Model: {model_name})")
    print(f"[CHAT] User: {user.email} (ID: {user.id})")
    print(f"[CHAT] Application: {app_name}")
    print(f"[CHAT] RAG ID: {rag_id or 'None'}")
    print(f"[CHAT] AIDR Collector: {collector_name}")
    print(f"[CHAT] Security Shield: {'ACTIVE' if message.security_enabled else 'BYPASS'}")
    print(f"[CHAT] History: {len(chat_history)} messages")
    
    # ========================================
    # Step 1: AIDR Input Scan (CONDITIONAL)
    # ========================================
    user_content = message.content
    
    if message.security_enabled:
        if aidr_token and aidr_url:
            aidr_client = AIGuardClient(base_url_template=aidr_url, token=aidr_token)
            security_service = SecurityService(client=aidr_client)
        else:
            security_service = SecurityService()
        
        print(f"[AIDR] Input Scan - user_email: {user.email}, llm_provider: {engine_name}, model: {model_name}, app_name: {app_name}")
        
        input_scan = security_service.scan_input(
            content=message.content,
            user_id=str(user.id),
            user_email=user.email,
            llm_provider=engine_name,
            model=model_name,
            app_name=app_name
        )
        
        if not input_scan.allowed:
            print(f"[AIDR] Input BLOCKED: {input_scan.error_message}")
            # Save blocked message to conversation
            with ConversationService() as conv_service:
                conv_service.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content="",
                    blocked=True,
                    violation_reason=input_scan.error_message,
                    security_enabled=message.security_enabled
                )
            return ChatResponse(
                response="",
                blocked=True,
                violation_reason=input_scan.error_message,
                context=context_info,
                conversation_id=conversation_id
            )
        
        user_content = input_scan.transformed_content if input_scan.transformed else message.content
    else:
        print(f"[WARNING] ========================================")
        print(f"[WARNING] Security Bypass enabled for User [{user.email}]")
        print(f"[WARNING] Proceeding without AIDR input scan.")
        print(f"[WARNING] ========================================")
    
    # ========================================
    # Step 2: RAG Retrieval (if agent has knowledge base)
    # ========================================
    rag_context = ""
    
    if rag_id:
        print(f"[RAG] Retrieving context from RAG ID: {rag_id}")
        try:
            vector_store = get_vector_store_service()
            rag_context = vector_store.get_context_for_query(
                rag_id=rag_id,
                query_text=user_content,
                max_tokens=2000
            )
            print(f"[RAG] Retrieved {len(rag_context)} chars of context")
        except Exception as e:
            print(f"[RAG] Retrieval error: {e}")
    else:
        print(f"[RAG] No RAG associated with current agent")
    
    # ========================================
    # Step 3: LLM Generation (with MCP tool calling support)
    # ========================================

    if rag_context:
        enhanced_system_prompt = f"{system_prompt}\n\n{rag_context}"
    else:
        enhanced_system_prompt = system_prompt

    llm_response = ""

    if engine and engine.api_key_encrypted:
        try:
            provider = get_provider_from_engine(engine)
            from app.services.llm.base import Message
            history_messages = [Message(role=m["role"], content=m["content"]) for m in chat_history]

            # Get MCP tool schemas if agent has an MCP server
            mcp_tools = None
            mcp_executor = None
            if mcp_server_id and mcp_config:
                from app.services.mcp_executor import get_mcp_executor
                mcp_executor = get_mcp_executor(
                    server_name=mcp_server_name or "Aegis Test Server",
                    server_config=mcp_config
                )
                if mcp_executor.is_available:
                    mcp_tools = mcp_executor.tool_schemas
                    print(f"[MCP] Passing {len(mcp_tools)} tool schemas to LLM")

            # Tool calling loop (max 5 rounds to prevent infinite loops)
            MAX_TOOL_ROUNDS = 5
            current_messages = history_messages.copy() if history_messages else []
            current_prompt = user_content

            for round_num in range(MAX_TOOL_ROUNDS + 1):
                response = provider.generate_response(
                    prompt=current_prompt,
                    system_prompt=enhanced_system_prompt,
                    history=current_messages if current_messages else None,
                    temperature=0.7,
                    max_tokens=4096,
                    tools=mcp_tools if round_num == 0 else None  # Only pass tools on first round
                )

                # Check if LLM returned tool calls
                if response.tool_calls and mcp_executor and round_num < MAX_TOOL_ROUNDS:
                    print(f"[MCP] Round {round_num + 1}: LLM requested {len(response.tool_calls)} tool calls")

                    # Add assistant message with tool calls to history
                    current_messages.append(Message(role="assistant", content=response.content or ""))

                    # Execute each tool call
                    tool_results = mcp_executor.execute_tool_calls(response.tool_calls)

                    # Build tool results message for the LLM
                    tool_results_text = ""
                    for tr in tool_results:
                        tool_results_text += f"\n--- Tool: {tr['tool_name']} ---\n{tr['result']}\n"

                    # Add tool results as a user message for the next round
                    current_messages.append(Message(
                        role="user",
                        content=f"Tool execution results:\n{tool_results_text}\n\nPlease provide your final response based on these results."
                    ))

                    current_prompt = ""  # Clear prompt since we're continuing the conversation
                    print(f"[MCP] Executed tools, sending results back to LLM")
                    continue

                # No tool calls - this is the final response
                llm_response = response.content
                break

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"[LLM] Generation failed: {e}")
            print(f"[LLM] Traceback: {error_detail}")
            with ConversationService() as conv_service:
                conv_service.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content="",
                    blocked=True,
                    violation_reason=f"LLM generation failed: {str(e) or 'Unknown error - check server logs'}",
                    security_enabled=message.security_enabled
                )
            return ChatResponse(
                response="",
                blocked=True,
                violation_reason=f"LLM generation failed: {str(e) or 'Unknown error - check server logs'}",
                context=context_info,
                conversation_id=conversation_id
            )
    else:
        if not message.engine_id:
            llm_response = (
                "No AI engine selected. Please select an engine from the dropdown to chat. "
                "You can configure engines in Settings > Engine Bank."
            )
        elif engine and not engine.api_key_encrypted:
            llm_response = (
                f"The selected engine ({engine.display_name}) has no API key configured. "
                "Please add an API key in Settings > Engine Bank."
            )
        else:
            llm_response = (
                f"[Demo Mode] Thank you for your message. "
                f"Your query was: '{user_content[:100]}{'...' if len(user_content) > 100 else ''}'"
            )
            if rag_context:
                llm_response += "\n\n[RAG Context was retrieved and would be used with a configured engine]"
    
    # ========================================
    # Step 4: AIDR Output Scan (CONDITIONAL)
    # ========================================
    final_response = llm_response
    
    if message.security_enabled:
        print(f"[AIDR] Output Scan - user_email: {user.email}, llm_provider: {engine_name}, model: {model_name}, app_name: {app_name}")
        
        if 'security_service' not in dir():
            security_service = SecurityService()
        
        output_scan = security_service.scan_output(
            content=llm_response,
            user_id=str(user.id),
            user_email=user.email,
            llm_provider=engine_name,
            model=model_name,
            app_name=app_name
        )
        
        if not output_scan.allowed:
            print(f"[AIDR] Output BLOCKED: {output_scan.error_message}")
            with ConversationService() as conv_service:
                conv_service.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content="",
                    blocked=True,
                    violation_reason=output_scan.error_message,
                    security_enabled=message.security_enabled
                )
            return ChatResponse(
                response="",
                blocked=True,
                violation_reason=output_scan.error_message,
                context=context_info,
                conversation_id=conversation_id
            )
        
        final_response = output_scan.transformed_content if output_scan.transformed else llm_response
    else:
        print(f"[WARNING] Security Bypass: Skipping AIDR output scan for User [{user.email}]")
    
    # ========================================
    # Step 5: Save assistant response and return
    # ========================================
    with ConversationService() as conv_service:
        conv_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=final_response,
            blocked=False,
            security_enabled=message.security_enabled
        )
        
        # Update conversation title based on first user message if still "New Chat"
        conv = conv_service.get_conversation(conversation_id)
        if conv and conv.title == "New Chat":
            # Generate title from first user message (truncate intelligently)
            title = message.content[:50]
            if len(message.content) > 50:
                # Try to break at word boundary
                last_space = title.rfind(' ')
                if last_space > 30:
                    title = title[:last_space]
                title += "..."
            conv_service.update_conversation(conversation_id, title=title)
            print(f"[CHAT] Updated conversation title: {title}")
    
    print(f"[CHAT] === Request Complete ===")
    print(f"[CHAT] Response length: {len(final_response)} chars")
    print(f"[CHAT] Security: {'Protected' if message.security_enabled else 'UNPROTECTED (Bypass)'}")
    
    return ChatResponse(
        response=final_response,
        blocked=False,
        context=context_info,
        conversation_id=conversation_id
    )


# ============================================================
# Legacy RAG File Upload Endpoint (kept for compatibility)
# New endpoints are under /api/rags/{rag_id}/files
# ============================================================
@app.get("/api/rag/files")
async def list_all_rag_files(rag_id: Optional[int] = None, email: str = Depends(verify_token)):
    """List all RAG files or files for a specific RAG"""
    with RAGService() as service:
        if rag_id:
            files = service.list_files_by_rag(rag_id)
        else:
            # List files from all RAGs
            files = []
            rags = service.list_rags(active_only=True)
            for rag in rags:
                rag_files = service.list_files_by_rag(rag.id)
                for f in rag_files:
                    files.append({
                        "id": f.id,
                        "filename": f.filename,
                        "size": f.file_size,
                        "rag_id": f.rag_id,
                        "rag_name": rag.name
                    })
            return files
        
        return [{"id": f.id, "filename": f.filename, "size": f.file_size, "rag_id": f.rag_id} for f in files]


# ============================================================
# Static Files & Frontend
# ============================================================
# Serve static files from frontend directory
frontend_path = Path(__file__).parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main frontend"""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>Aegis AI - Frontend not found</h1>")


@app.get("/favicon.ico")
async def favicon():
    """Serve favicon"""
    favicon_path = Path(__file__).parent / "app" / "static" / "favicon.svg"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/svg+xml")
    raise HTTPException(status_code=404)


@app.get("/logo.svg")
async def logo():
    """Serve logo"""
    logo_path = Path(__file__).parent / "app" / "static" / "logo.svg"
    if logo_path.exists():
        return FileResponse(logo_path, media_type="image/svg+xml")
    raise HTTPException(status_code=404)


# ============================================================
# Health Check
# ============================================================
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Aegis AI", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=15000)
