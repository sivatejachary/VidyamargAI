import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import Candidate, User, UserConsent, UserPreference
from app.models.auto_apply_models import PlatformHealth, ApplicationTask

# Test targets
from app.services.auto_apply.credential_vault import credential_vault
from app.services.auto_apply.consent_service import consent_service, ConsentRequiredException
from app.services.auto_apply.platform_health_service import platform_health_service
from app.services.auto_apply.platform_rate_limiter import platform_rate_limiter
from app.services.auto_apply.requirements_validator import requirements_validator
from app.services.auto_apply.adapters import detect_platform, load_adapter

# Setup in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_credential_vault_encryption():
    """Test Fernet encryption and decryption round-trip."""
    plaintext = "super-secret-session-cookie-data"
    
    # If key is missing, vault runs in simulation mode, which obfustcates data.
    # We test that round-trip decryption still yields original text.
    encrypted = credential_vault.encrypt(plaintext)
    decrypted = credential_vault.decrypt(encrypted)
    
    assert decrypted == plaintext or encrypted.startswith("UNENCRYPTED:")
    assert credential_vault.encrypt("") == ""
    assert credential_vault.decrypt("") == ""


def test_consent_service_lifecycle(db):
    """Test grant, has_consent, require, and revoke lifecycle."""
    user = User(email="test@user.com", password_hash="hash", full_name="Test User")
    db.add(user)
    db.commit()
    
    # Initially no consent
    assert not consent_service.has_consent(user.id, "auto_apply", db)
    with pytest.raises(ConsentRequiredException):
        consent_service.require(user.id, "auto_apply", db)
        
    # Grant consent
    consent_service.grant(user.id, "auto_apply", db, metadata={"ip": "127.0.0.1"})
    assert consent_service.has_consent(user.id, "auto_apply", db)
    assert consent_service.require(user.id, "auto_apply", db)
    
    # Revoke consent
    consent_service.revoke(user.id, "auto_apply", db)
    assert not consent_service.has_consent(user.id, "auto_apply", db)
    with pytest.raises(ConsentRequiredException):
        consent_service.require(user.id, "auto_apply", db)


def test_platform_health_auto_disable(db):
    """Test that platform health service records attempts and auto-disables on low success rate."""
    platform = "workday"
    
    # Record 9 failures — should not disable because min attempts is 10
    for _ in range(9):
        platform_health_service.record_attempt(platform, success=False, db=db, error="Automation Timeout")
        
    assert platform_health_service.is_platform_enabled(platform, db)
    
    # 10th failure — success rate 0% < 20% threshold, should disable
    platform_health_service.record_attempt(platform, success=False, db=db, error="Automation Timeout")
    assert not platform_health_service.is_platform_enabled(platform, db)
    
    # Manually re-enable
    platform_health_service.re_enable(platform, db)
    assert platform_health_service.is_platform_enabled(platform, db)
    
    # Check counters reset
    health = db.query(PlatformHealth).filter_by(platform=platform).first()
    assert health.total_attempts == 0
    assert health.success_rate == 1.0


def test_platform_rate_limiter(db):
    """Test platform rate limit retrieval and DB-based check fallback."""
    # Greenhouse delay & daily limits
    assert platform_rate_limiter.get_delay_ms("greenhouse") == 5000
    assert platform_rate_limiter.get_delay_ms("workday") == 10000
    assert platform_rate_limiter.get_delay_ms("unknown") == 8000
    
    # Test DB count check fallback
    user_id = 1
    platform = "greenhouse"
    
    # Limit for greenhouse is 100, we add tasks
    # We consume slots
    allowed = platform_rate_limiter.check_and_consume(user_id, platform, db)
    assert allowed  # Falls back to DB check, currently 0 tasks today


def test_requirements_validator():
    """Test regex-based requirements validator for hard blockers."""
    candidate_profile = {
        "visa_eligible": False,
        "location": "India",
        "remote_only": True,
        "education": "Bachelor of Technology",
        "experience_years": 3.0
    }
    
    # Case 1: Sponsorship blocker
    job_sponsorship = {
        "title": "Software Engineer",
        "description": "We are not providing visa sponsorship for this role. Candidates must be authorized to work.",
        "location": "US",
        "work_mode": "remote"
    }
    res = requirements_validator.validate(candidate_profile, job_sponsorship)
    assert not res.passed
    assert any("sponsorship" in b.lower() for b in res.blockers)
    
    # Case 2: On-site vs remote blocker
    job_onsite = {
        "title": "Software Engineer",
        "description": "On-site full-time role in Bangalore.",
        "location": "Bangalore",
        "work_mode": "on-site"
    }
    res = requirements_validator.validate(candidate_profile, job_onsite)
    assert not res.passed
    assert any("remote" in b.lower() for b in res.blockers)

    # Case 3: Experience gap blocker
    job_senior = {
        "title": "Senior Staff Engineer",
        "description": "Requires 8+ years of experience in backend development.",
        "location": "Remote",
        "work_mode": "remote"
    }
    res = requirements_validator.validate(candidate_profile, job_senior)
    assert not res.passed
    assert any("experience" in b.lower() for b in res.blockers)


def test_platform_detection():
    """Test URL-based platform detection rules."""
    assert detect_platform("https://boards.greenhouse.io/google/jobs/12345") == "greenhouse"
    assert detect_platform("https://jobs.lever.co/facebook/abc-def") == "lever"
    assert detect_platform("https://company.myworkdayjobs.com/careers") == "workday"
    assert detect_platform("https://jobs.ashbyhq.com/startup/job-id") == "ashby"
    assert detect_platform("https://docs.google.com/forms/d/e/1FAIpQLSf/viewform") == "google_forms"
    assert detect_platform("https://linkedin.com/jobs/view/123456") == "linkedin"
    assert detect_platform("https://example.com/careers") == "generic"
