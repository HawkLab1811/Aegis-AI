"""Conversation management service for Aegis AI."""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.conversation import Conversation, ConversationMessage


class ConversationService:
    """Service for managing conversations and their messages."""

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

    def create_conversation(
        self,
        user_id: int,
        title: str = "New Chat",
        agent_id: Optional[int] = None,
        engine_id: Optional[int] = None,
        collector_id: Optional[int] = None,
        app_name: Optional[str] = None
    ) -> Conversation:
        conv = Conversation(
            user_id=user_id,
            title=title,
            agent_id=agent_id,
            engine_id=engine_id,
            collector_id=collector_id,
            app_name=app_name,
            is_active=True
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def get_conversation(self, conv_id: int) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(Conversation.id == conv_id).first()

    def list_conversations(self, user_id: int, active_only: bool = True) -> List[Conversation]:
        query = self.db.query(Conversation).filter(Conversation.user_id == user_id)
        if active_only:
            query = query.filter(Conversation.is_active == True)
        return query.order_by(Conversation.updated_at.desc()).all()

    def update_conversation(
        self,
        conv_id: int,
        title: Optional[str] = None,
        agent_id: Optional[int] = None,
        engine_id: Optional[int] = None,
        collector_id: Optional[int] = None,
        app_name: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Conversation]:
        conv = self.get_conversation(conv_id)
        if not conv:
            return None
        if title is not None:
            conv.title = title
        if agent_id is not None:
            conv.agent_id = agent_id
        if engine_id is not None:
            conv.engine_id = engine_id
        if collector_id is not None:
            conv.collector_id = collector_id
        if app_name is not None:
            conv.app_name = app_name
        if is_active is not None:
            conv.is_active = is_active
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def delete_conversation(self, conv_id: int) -> bool:
        conv = self.get_conversation(conv_id)
        if not conv:
            return False
        self.db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conv_id
        ).delete()
        self.db.delete(conv)
        self.db.commit()
        return True

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        blocked: bool = False,
        violation_reason: Optional[str] = None,
        security_enabled: bool = True
    ) -> ConversationMessage:
        msg = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            blocked=blocked,
            violation_reason=violation_reason,
            security_enabled=security_enabled
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_messages(
        self,
        conversation_id: int,
        limit: int = 50
    ) -> List[ConversationMessage]:
        return (
            self.db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
            .all()
        )

    def get_history_for_llm(
        self,
        conversation_id: int,
        max_messages: int = 20
    ) -> list:
        messages = self.get_messages(conversation_id, limit=max_messages)
        history = []
        for msg in messages:
            if msg.role in ("user", "assistant") and not msg.blocked:
                history.append({"role": msg.role, "content": msg.content})
        return history
