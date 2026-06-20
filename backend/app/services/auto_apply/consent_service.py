"""
Consent Service — Checks and manages user consent for automation features.
Every automation action must call require() before proceeding.
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ConsentRequiredException(Exception):
    """Raised when required user consent is missing or revoked."""
    def __init__(self, consent_type: str):
        self.consent_type = consent_type
        super().__init__(f"User consent required: '{consent_type}'. Please grant consent before proceeding.")


class ConsentService:
    """
    Manages user consent for all automation features.
    
    Consent types:
      - auto_apply               : Enable automated form submission
      - credential_storage       : Store login sessions for a platform
      - cover_letter_generation  : Allow LLM to generate cover letters
      - screening_answer_generation: Allow LLM to answer screening questions
      - app_submission           : Submit applications on behalf of user
      - account_access           : Log into career portals
      - resume_upload            : Upload resume to third-party portals
      - data_storage             : General data retention
    """

    def require(self, user_id: int, consent_type: str, db: Session) -> bool:
        """
        Check if consent is granted and not revoked.
        Raises ConsentRequiredException if not granted.
        """
        try:
            from app.models.models import UserConsent
            consent = db.query(UserConsent).filter(
                UserConsent.user_id == user_id,
                UserConsent.consent_type == consent_type,
                UserConsent.granted == True,
                UserConsent.revoked_at == None  # noqa: E711
            ).first()
            if not consent:
                raise ConsentRequiredException(consent_type)
            return True
        except ConsentRequiredException:
            raise
        except Exception as e:
            logger.error(f"Consent check failed for user {user_id}, type {consent_type}: {e}")
            raise ConsentRequiredException(consent_type)

    def has_consent(self, user_id: int, consent_type: str, db: Session) -> bool:
        """
        Returns True/False without raising. Use for conditional checks.
        """
        try:
            self.require(user_id, consent_type, db)
            return True
        except ConsentRequiredException:
            return False

    def grant(self, user_id: int, consent_type: str, db: Session, metadata: Optional[dict] = None) -> None:
        """
        Grant or re-grant consent. Updates existing record if present.
        """
        from app.models.models import UserConsent
        import uuid
        consent = db.query(UserConsent).filter(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == consent_type
        ).first()
        if consent:
            consent.granted = True
            consent.granted_at = datetime.utcnow()
            consent.revoked_at = None
            if metadata:
                existing = consent.metadata_json or {}
                existing.update(metadata)
                consent.metadata_json = existing
        else:
            consent = UserConsent(
                user_id=user_id,
                consent_type=consent_type,
                granted=True,
                granted_at=datetime.utcnow(),
                consent_ref=str(uuid.uuid4()),
                metadata_json=metadata or {}
            )
            db.add(consent)
        db.commit()

    def revoke(self, user_id: int, consent_type: str, db: Session) -> None:
        """
        Revoke consent. Sets revoked_at timestamp — record is NOT deleted.
        """
        from app.models.models import UserConsent
        consent = db.query(UserConsent).filter(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == consent_type
        ).first()
        if consent:
            consent.granted = False
            consent.revoked_at = datetime.utcnow()
            db.commit()


# Module-level singleton
consent_service = ConsentService()