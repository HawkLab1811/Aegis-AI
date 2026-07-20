"""Profile service for managing user configuration presets."""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.core.database import SessionLocal


class ProfileService:
    """Service for managing user profiles."""

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

    def get_all(self, active_only: bool = False) -> List[Profile]:
        """Get all profiles."""
        query = self.db.query(Profile)
        if active_only:
            query = query.filter(Profile.is_active == True)
        return query.order_by(Profile.name).all()

    def get_by_id(self, profile_id: int) -> Optional[Profile]:
        """Get profile by ID."""
        return self.db.query(Profile).filter(Profile.id == profile_id).first()

    def get_by_name(self, name: str) -> Optional[Profile]:
        """Get profile by name."""
        return self.db.query(Profile).filter(Profile.name == name).first()

    def get_default(self) -> Optional[Profile]:
        """Get the default profile."""
        return self.db.query(Profile).filter(
            Profile.is_default == True,
            Profile.is_active == True
        ).first()

    def create(
        self,
        name: str,
        description: Optional[str] = None,
        agent_id: Optional[int] = None,
        user_id: Optional[int] = None,
        engine_id: Optional[int] = None,
        collector_id: Optional[int] = None,
        app_name: Optional[str] = None,
        is_default: bool = False
    ) -> Profile:
        """Create a new profile."""
        # If this is set as default, unset other defaults
        if is_default:
            self.db.query(Profile).filter(
                Profile.is_default == True
            ).update({"is_default": False})
        
        profile = Profile(
            name=name,
            description=description,
            agent_id=agent_id,
            user_id=user_id,
            engine_id=engine_id,
            collector_id=collector_id,
            app_name=app_name,
            is_default=is_default,
            is_active=True
        )
        
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update(
        self,
        profile_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        agent_id: Optional[int] = None,
        user_id: Optional[int] = None,
        engine_id: Optional[int] = None,
        collector_id: Optional[int] = None,
        app_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_default: Optional[bool] = None,
        clear_agent: bool = False,
        clear_user: bool = False,
        clear_engine: bool = False,
        clear_collector: bool = False,
        clear_app: bool = False
    ) -> Optional[Profile]:
        """Update a profile."""
        profile = self.get_by_id(profile_id)
        if not profile:
            return None
        
        if name is not None:
            profile.name = name
        if description is not None:
            profile.description = description
        
        # Handle clearing vs setting values
        if clear_agent:
            profile.agent_id = None
        elif agent_id is not None:
            profile.agent_id = agent_id
            
        if clear_user:
            profile.user_id = None
        elif user_id is not None:
            profile.user_id = user_id
            
        if clear_engine:
            profile.engine_id = None
        elif engine_id is not None:
            profile.engine_id = engine_id
            
        if clear_collector:
            profile.collector_id = None
        elif collector_id is not None:
            profile.collector_id = collector_id
            
        if clear_app:
            profile.app_name = None
        elif app_name is not None:
            profile.app_name = app_name
        
        if is_active is not None:
            profile.is_active = is_active
            
        if is_default is not None:
            if is_default:
                # Unset other defaults
                self.db.query(Profile).filter(
                    Profile.id != profile_id,
                    Profile.is_default == True
                ).update({"is_default": False})
            profile.is_default = is_default
        
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def delete(self, profile_id: int) -> bool:
        """Soft delete a profile (deactivate)."""
        profile = self.get_by_id(profile_id)
        if not profile:
            return False
        
        profile.is_active = False
        if profile.is_default:
            profile.is_default = False
        
        self.db.commit()
        return True

    def hard_delete(self, profile_id: int) -> bool:
        """Permanently delete a profile."""
        profile = self.get_by_id(profile_id)
        if not profile:
            return False
        
        self.db.delete(profile)
        self.db.commit()
        return True

    def get_profile_with_details(self, profile_id: int) -> Optional[dict]:
        """Get profile with resolved entity names."""
        from app.services.agent_service import AgentService
        from app.services.user_service import UserService
        from app.services.ai_engine_service import AIEngineService
        from app.services.aidr_collector_service import AIDRCollectorService
        
        profile = self.get_by_id(profile_id)
        if not profile:
            return None
        
        result = {
            "id": profile.id,
            "name": profile.name,
            "description": profile.description,
            "agent_id": profile.agent_id,
            "agent_name": None,
            "user_id": profile.user_id,
            "user_email": None,
            "engine_id": profile.engine_id,
            "engine_name": None,
            "collector_id": profile.collector_id,
            "collector_name": None,
            "app_name": profile.app_name,
            "is_active": profile.is_active,
            "is_default": profile.is_default
        }
        
        # Resolve names
        if profile.agent_id:
            with AgentService() as svc:
                agent = svc.get_agent_by_id(profile.agent_id)
                if agent:
                    result["agent_name"] = agent.name
        
        if profile.user_id:
            with UserService() as svc:
                user = svc.get_user_by_id(profile.user_id)
                if user:
                    result["user_email"] = user.email
        
        if profile.engine_id:
            with AIEngineService() as svc:
                engine = svc.get_engine_by_id(profile.engine_id)
                if engine:
                    result["engine_name"] = engine.display_name
        
        if profile.collector_id:
            with AIDRCollectorService() as svc:
                collector = svc.get_by_id(profile.collector_id)
                if collector:
                    result["collector_name"] = collector.name
        
        return result
