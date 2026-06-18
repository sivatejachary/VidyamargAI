"""
Session Manager — stores, retrieves, and invalidates session cookies
for portal automation logins, enabling session persistence across browser contexts.
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.session_models import BrowserSession, BrowserCookie

logger = logging.getLogger("app.session_manager")


class SessionManager:
    """Manages automation cookies and login sessions in the database."""

    def save_session(
        self,
        user_id: int,
        portal: str,
        username: str,
        cookies: List[Dict[str, Any]],
        db: Session
    ) -> BrowserSession:
        """Saves a list of Playwright cookies to the database for future logins."""
        # Find existing session
        session = db.query(BrowserSession).filter(
            BrowserSession.user_id == user_id,
            BrowserSession.portal == portal
        ).first()

        if not session:
            session = BrowserSession(
                user_id=user_id,
                portal=portal,
                username=username,
                status="active"
            )
            db.add(session)
            db.commit()
            db.refresh(session)
        else:
            session.username = username
            session.status = "active"
            session.updated_at = session.updated_at # Trigger update hook
            db.commit()

        # Update or create cookies record
        cookie_record = db.query(BrowserCookie).filter(
            BrowserCookie.session_id == session.id
        ).first()

        if not cookie_record:
            cookie_record = BrowserCookie(
                session_id=session.id,
                cookie_data=cookies
            )
            db.add(cookie_record)
        else:
            cookie_record.cookie_data = cookies
        
        db.commit()
        logger.info(f"Saved session cookies for user {user_id} on {portal}. Cookie count: {len(cookies)}")
        return session

    async def restore_session_to_context(
        self,
        user_id: int,
        portal: str,
        context: Any,
        db: Session
    ) -> bool:
        """Restores saved cookies to an active Playwright browser context."""
        if not context:
            logger.debug("Cannot restore cookies to a null context.")
            return False

        session = db.query(BrowserSession).filter(
            BrowserSession.user_id == user_id,
            BrowserSession.portal == portal,
            BrowserSession.status == "active"
        ).first()

        if not session:
            logger.debug(f"No active session found for user {user_id} on {portal}.")
            return False

        cookie_record = db.query(BrowserCookie).filter(
            BrowserCookie.session_id == session.id
        ).first()

        if not cookie_record or not cookie_record.cookie_data:
            logger.debug(f"No cookies found for session {session.id}.")
            return False

        try:
            cookies_list = cookie_record.cookie_data
            if isinstance(cookies_list, list):
                await context.add_cookies(cookies_list)
                logger.info(f"Restored {len(cookies_list)} cookies for user {user_id} on {portal}.")
                return True
        except Exception as exc:
            logger.error(f"Failed to restore cookies to context: {exc}")
            # Expire session on cookie injection failure
            self.invalidate_session(user_id, portal, db)

        return False

    def invalidate_session(self, user_id: int, portal: str, db: Session):
        """Marks a session as expired when logins fail or cookies are rejected."""
        session = db.query(BrowserSession).filter(
            BrowserSession.user_id == user_id,
            BrowserSession.portal == portal
        ).first()

        if session and session.status != "expired":
            session.status = "expired"
            db.commit()
            logger.info(f"Session invalidated (expired) for user {user_id} on {portal}.")


session_manager = SessionManager()
