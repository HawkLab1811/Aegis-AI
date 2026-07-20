"""Application service for managing application names."""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.application import Application


class ApplicationService:
    """Service for managing application names."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self, active_only: bool = False) -> List[Application]:
        """Get all applications."""
        query = self.db.query(Application)
        if active_only:
            query = query.filter(Application.is_active == True)
        return query.order_by(Application.name).all()

    def get_by_id(self, app_id: int) -> Optional[Application]:
        """Get application by ID."""
        return self.db.query(Application).filter(Application.id == app_id).first()

    def get_by_name(self, name: str) -> Optional[Application]:
        """Get application by name."""
        return self.db.query(Application).filter(Application.name == name).first()

    def get_default(self) -> Optional[Application]:
        """Get the default application."""
        return self.db.query(Application).filter(
            Application.is_default == True,
            Application.is_active == True
        ).first()

    def create(self, name: str, description: Optional[str] = None, is_default: bool = False) -> Application:
        """Create a new application."""
        # If setting as default, unset other defaults
        if is_default:
            self.db.query(Application).filter(Application.is_default == True).update(
                {"is_default": False}
            )
        
        application = Application(
            name=name,
            description=description,
            is_default=is_default
        )
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        return application

    def update(self, app_id: int, name: Optional[str] = None, description: Optional[str] = None,
               is_active: Optional[bool] = None, is_default: Optional[bool] = None) -> Optional[Application]:
        """Update an application."""
        application = self.get_by_id(app_id)
        if not application:
            return None

        if name is not None:
            application.name = name
        if description is not None:
            application.description = description
        if is_active is not None:
            application.is_active = is_active
        if is_default is not None:
            # If setting as default, unset other defaults
            if is_default:
                self.db.query(Application).filter(
                    Application.is_default == True,
                    Application.id != app_id
                ).update({"is_default": False})
            application.is_default = is_default

        self.db.commit()
        self.db.refresh(application)
        return application

    def delete(self, app_id: int) -> bool:
        """Delete an application (soft delete by deactivating)."""
        application = self.get_by_id(app_id)
        if not application:
            return False
        
        application.is_active = False
        self.db.commit()
        return True

    def hard_delete(self, app_id: int) -> bool:
        """Permanently delete an application."""
        application = self.get_by_id(app_id)
        if not application:
            return False
        
        self.db.delete(application)
        self.db.commit()
        return True
