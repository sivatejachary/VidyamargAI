import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import TelegramSource
from app.services.job_discovery.telegram_connector import TelegramJobsConnector

def test_telegram_connector_search():
    # Set up in-memory sqlite db
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    try:
        # Seed test telegram source
        source = TelegramSource(channel_name="swiggy_openings", active=True)
        db.add(source)
        db.commit()
        
        # Patch the db session local inside the connector to use our memory db
        with patch("app.core.database.SessionLocal", return_value=db):
            connector = TelegramJobsConnector()
            
            # 1. Test successful scraping mock fallback
            jobs = connector.search(roles=["Developer"], locations=["Bangalore"], skills=["Python"])
            assert len(jobs) > 0
            assert jobs[0]["company_name"] == "Swiggy"
            assert jobs[0]["source_name"] == "telegram"
            assert "swiggy" in jobs[0]["apply_url"]
            
            # 2. Test experience parsing helper
            assert connector._parse_experience("1-3 years") == (1.0, 3.0)
            assert connector._parse_experience("Fresher") == (0.0, 1.0)
            
            # 3. Test company name cleaning helper
            msg = "🚨 Swiggy off campus hiring for Software Engineer Role | swiggy_openings"
            assert connector.clean_company_name("Swiggy", msg) == "Swiggy"
            
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
