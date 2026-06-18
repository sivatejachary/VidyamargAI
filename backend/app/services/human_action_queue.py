"""
Human Action Queue — for anything AI cannot safely do autonomously.

When an agent encounters CAPTCHA, OTP, 2FA, payment, or recruiter questions,
it raises HumanActionRequired. This service stores the item and lets the
frontend notify the user with a ⚠ "Complete Now" banner.
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models.mcp_models import HumanActionItem

logger = logging.getLogger("app.services.haq")


class HumanActionRequired(Exception):
    """
    Raised by agents when human input is required to continue.
    Caught by the Supervisor Agent which persists it to the HAQ.
    """
    def __init__(
        self,
        action_type: str,
        title: str,
        description: str,
        payload: dict,
        expires_minutes: int = 30
    ):
        super().__init__(title)
        self.action_type = action_type  # "captcha", "otp", "2fa", "payment", "manual_review", "recruiter_question"
        self.title = title
        self.description = description
        self.payload = payload
        self.callback_key = str(uuid.uuid4())
        self.expires_minutes = expires_minutes


class HumanActionQueue:
    """Service for managing the Human Action Queue."""

    def create(
        self,
        user_id: int,
        agent_name: str,
        exc: HumanActionRequired,
        db: Session
    ) -> HumanActionItem:
        """Persists a pending human action item."""
        item = HumanActionItem(
            user_id=user_id,
            agent_name=agent_name,
            action_type=exc.action_type,
            title=exc.title,
            description=exc.description,
            status="pending",
            payload=exc.payload,
            callback_key=exc.callback_key,
            expires_at=datetime.utcnow() + timedelta(minutes=exc.expires_minutes),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        logger.info(f"HAQ item created: user={user_id}, type={exc.action_type}, key={exc.callback_key}")
        return item

    def complete(
        self,
        callback_key: str,
        human_input: dict,
        db: Session
    ) -> Optional[HumanActionItem]:
        """Called when user completes the required action."""
        item = db.query(HumanActionItem).filter(
            HumanActionItem.callback_key == callback_key
        ).first()
        if not item:
            return None
        item.status = "completed"
        item.payload = {**(item.payload or {}), "human_input": human_input}
        item.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"HAQ item completed: key={callback_key}")
        return item

    def dismiss(
        self,
        callback_key: str,
        db: Session
    ) -> Optional[HumanActionItem]:
        """User dismisses an action (skips it)."""
        item = db.query(HumanActionItem).filter(
            HumanActionItem.callback_key == callback_key
        ).first()
        if not item:
            return None
        item.status = "dismissed"
        db.commit()
        return item

    def get_pending(
        self,
        user_id: int,
        db: Session
    ) -> list[HumanActionItem]:
        """Returns all pending items for a user, expiring stale ones first."""
        # Mark expired items
        now = datetime.utcnow()
        db.query(HumanActionItem).filter(
            HumanActionItem.user_id == user_id,
            HumanActionItem.status == "pending",
            HumanActionItem.expires_at < now
        ).update({"status": "expired"})
        db.commit()
        return db.query(HumanActionItem).filter(
            HumanActionItem.user_id == user_id,
            HumanActionItem.status == "pending"
        ).order_by(HumanActionItem.created_at.desc()).all()

    def is_completed(self, callback_key: str, db: Session) -> bool:
        """Agent polls this to check if the user completed their action."""
        item = db.query(HumanActionItem).filter(
            HumanActionItem.callback_key == callback_key
        ).first()
        return item is not None and item.status == "completed"


haq_service = HumanActionQueue()
