"""
Agent management service for Aegis AI.

Handles Agent CRUD operations.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.agent import Agent


class AgentService:
    """Service for managing Agents."""
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the agent service.
        
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
    
    def create_agent(
        self,
        name: str,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        rag_id: Optional[int] = None,
        mcp_server_id: Optional[int] = None
    ) -> Agent:
        existing = self.get_agent_by_name(name)
        if existing:
            raise ValueError(f"Agent with name {name} already exists")

        agent = Agent(
            name=name,
            description=description,
            system_prompt=system_prompt,
            rag_id=rag_id,
            mcp_server_id=mcp_server_id,
            is_active=True
        )
        
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        
        return agent
    
    def get_agent_by_id(self, agent_id: int) -> Optional[Agent]:
        """Get agent by ID."""
        return self.db.query(Agent).filter(Agent.id == agent_id).first()
    
    def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """Get agent by name."""
        return self.db.query(Agent).filter(Agent.name == name).first()
    
    def list_agents(self, active_only: bool = True) -> List[Agent]:
        """List all agents."""
        query = self.db.query(Agent)
        if active_only:
            query = query.filter(Agent.is_active == True)
        return query.all()
    
    def update_agent(
        self,
        agent_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        rag_id: Optional[int] = None,
        mcp_server_id: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Agent]:
        """Update agent attributes."""
        agent = self.get_agent_by_id(agent_id)
        if not agent:
            return None
        
        if name is not None:
            agent.name = name
        if description is not None:
            agent.description = description
        if system_prompt is not None:
            agent.system_prompt = system_prompt
        if rag_id is not None:
            agent.rag_id = rag_id
        if mcp_server_id is not None:
            agent.mcp_server_id = mcp_server_id
        if is_active is not None:
            agent.is_active = is_active
        
        self.db.commit()
        self.db.refresh(agent)
        
        return agent
    
    def delete_agent(self, agent_id: int) -> bool:
        """Delete an agent (soft delete)."""
        agent = self.get_agent_by_id(agent_id)
        if not agent:
            return False
        
        agent.is_active = False
        self.db.commit()
        
        return True


def get_agent_service(db: Optional[Session] = None) -> AgentService:
    """Get an agent service instance."""
    return AgentService(db=db)
