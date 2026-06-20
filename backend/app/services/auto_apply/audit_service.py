"""
Audit Service — Structured compliance and debugging audit trail.
Every significant lifecycle action writes a typed record to ApplicationAudit.
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# All valid audit action strings
AUDIT_ACTIONS = frozenset({
    "TASK_QUEUED", "TASK_SKIPPED", "TASK_CANCELLED", "RATE_LIMITED",
    "CONSENT_CHECKED", "CONSENT_MISSING",
    "ACCOUNT_FOUND", "ACCOUNT_CREATED", "LOGIN_SUCCESS", "LOGIN_FAILED",
    "VERIFICATION_DETECTED", "OTP_SENT", "OTP_VERIFIED",
    "REVIEW_REQUIRED", "USER_APPROVED", "USER_REJECTED",
    "REQUIREMENTS_VALIDATED", "REQUIREMENTS_FAILED",
    "RESUME_SELECTED", "RESUME_UPLOADED",
    "FORM_FILLED", "COVER_LETTER_GENERATED", "QUESTION_ANSWERED",
    "APPLICATION_SUBMITTED", "SUBMISSION_FAILED", "CONFIRMATION_CAPTURED",
    "CHECKPOINT_SAVED", "CHECKPOINT_RESTORED",
    "PLATFORM_DISABLED", "ADAPTER_VERSION_LOGGED",
})


class AuditService:
    """
    Fire-and-forget audit logger. Never raises — audit failures are logged but do not
    block the critical application path.
    """

    def log(
        self,
        actor: str,
        action: str,
        db: Session,
        task_id: Optional[int] = None,
        run_id: Optional[int] = None,
        details: Optional[dict] = None
    ) -> None:
        """
        Write an audit record.

        Args:
            actor:   "system" | "user:{user_id}" | "adapter:{platform}"
            action:  One of AUDIT_ACTIONS
            db:      SQLAlchemy session
            task_id: Related ApplicationTask ID (optional)
            run_id:  Related ApplicationRun ID (optional)
            details: Any JSON-serializable dict for context
        """
        try:
            from app.models.auto_apply_models import ApplicationAudit
            if action not in AUDIT_ACTIONS:
                logger.warning(f"Unknown audit action '{action}' — writing anyway")
            entry = ApplicationAudit(
                task_id=task_id,
                run_id=run_id,
                actor=actor,
                action=action,
                timestamp=datetime.utcnow(),
                details=details or {}
            )
            db.add(entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to write audit log [{action}]: {e}")
            try:
                db.rollback()
            except Exception:
                pass


# Module-level singleton
audit_service = AuditService()