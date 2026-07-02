"""
VidyaMarg AI OS — Session Models
Database tables for browser session and cookie persistence.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class BrowserSession(Base):
    """
    Tracks browser automation sessions per user and job portal.
    """
    __tablename__ = "browser_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    portal = Column(String(100), nullable=False)           # "linkedin", "naukri", "indeed", "wellfound"
    username = Column(String(255), nullable=True)          # Login email/username used
    status = Column(String(50), default="active")          # "active", "expired"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cookies = relationship("BrowserCookie", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_bs_user_portal", "user_id", "portal"),
    )


class BrowserCookie(Base):
    """
    Serialized cookie payload for a browser session context.
    """
    __tablename__ = "browser_cookies"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("browser_sessions.id", ondelete="CASCADE"), nullable=False)
    cookie_data = Column(JSON, nullable=False)             # List of Playwright cookie dicts
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session = relationship("BrowserSession", back_populates="cookies")

    __table_args__ = (
        Index("idx_bc_session", "session_id"),
    )
