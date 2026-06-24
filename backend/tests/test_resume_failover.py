import pytest
import json
import uuid
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base
from app.models.models import Candidate, CandidateResume, CandidateProfile, User
from app.models.job_models import ResumeAIAnalysis
from app.services.orchestrator import fallback_pymupdf_pipeline
from app.agents.resume_intelligence_agent import ResumeIntelligenceAgent, ResumeState

@pytest.fixture(scope="function")
def db_session():
    import app.models.job_models  # Ensure job models are imported
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"test_failover_{unique_id}@example.com"
    try:
        # Create a mock user and candidate
        user = User(email=test_email, password_hash="hash", full_name="Failover Candidate")
        db.add(user)
        db.commit()
        db.refresh(user)

        candidate = Candidate(user_id=user.id, skills="Python, SQL", phone="1234567890", address="Delhi")
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        resume = CandidateResume(candidate_id=candidate.id, resume_url="http://example.com/test_failover.pdf", is_active=True)
        db.add(resume)
        db.commit()
        db.refresh(resume)

        profile = CandidateProfile(candidate_id=candidate.id, resume_id=resume.id, resume_text="Delhi. Email: test@example.com. Phone: 9876543210. Experience: Software Developer at Tech Pvt Ltd. Education: B.Tech at Delhi University.")
        db.add(profile)
        db.commit()
        db.refresh(profile)

        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_fallback_pymupdf_pipeline():
    # Test that the pipeline functions on empty bytes/mock data and produces correct keys
    mock_pdf_bytes = b"PDF dummy content"
    
    with patch("fitz.open") as mock_fitz_open:
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = (
            "Name: John Doe\n"
            "Email: john@example.com\n"
            "Phone: +919999999999\n"
            "Skills\n"
            "Python, React, Spring\n"
            "Experience\n"
            "Software Engineer at Acme Ltd 2021\n"
            "Education\n"
            "Delhi University - B.Tech degree 2022"
        )
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz_open.return_value = mock_doc
        
        res = fallback_pymupdf_pipeline(mock_pdf_bytes)
        
        assert res["name"] == "John Doe"
        assert res["email"] == "john@example.com"
        assert res["phone"] == "+919999999999"
        assert "Python" in res["skills"]
        assert len(res["experience"]) > 0
        assert len(res["education"]) > 0
        assert res["education"][0]["school"] == "Delhi University"
        assert res["parsed_json"]["career_classification"]["career_family"] == "Engineering"


@pytest.mark.asyncio
@patch("app.agents.resume_intelligence_agent.call_gemini")
@patch("app.agents.resume_intelligence_agent.call_nvidia")
@patch("app.services.embedding_service.EmbeddingService.get_nvidia_embedding")
@patch("app.services.vector_store.QdrantVectorStore.upsert_candidate_vector")
@patch("app.services.vector_store.QdrantVectorStore.upsert_resume")
async def test_agent_failover_to_fallback(
    mock_upsert_resume, 
    mock_upsert_vector, 
    mock_get_embedding, 
    mock_call_nvidia, 
    mock_call_gemini, 
    db_session
):
    # Mock Gemini Flash and Pro to throw/fail to test complete fallback pipeline
    mock_call_gemini.side_effect = Exception("API Outage - Service Unavailable")
    mock_call_nvidia.side_effect = Exception("API Outage - Service Unavailable")
    mock_get_embedding.return_value = [0.1] * 768
    mock_upsert_vector.return_value = True
    mock_upsert_resume.return_value = True

    # Find the candidate we created
    candidate = db_session.query(Candidate).join(User).filter(User.email.like("test_failover_%")).first()
    assert candidate is not None

    agent = ResumeIntelligenceAgent(db_session, candidate.id)
    
    # Run the graph
    final_state = await agent.execute_pipeline()
    
    # Assert it finished and generated career intelligence
    assert final_state is not None
    assert "career_intelligence" in final_state
    
    # Check that a ResumeAIAnalysis record was logged with source FALLBACK
    analysis_rec = db_session.query(ResumeAIAnalysis).filter(
        ResumeAIAnalysis.candidate_id == candidate.id
    ).order_by(ResumeAIAnalysis.created_at.desc()).first()
    
    assert analysis_rec is not None
    assert analysis_rec.source_type == "FALLBACK"
    assert analysis_rec.confidence_score == "MEDIUM"
    
    # Clean up the analysis log
    db_session.delete(analysis_rec)
    db_session.commit()


def test_get_resume_profile_endpoint(db_session):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db
    from app.api.routers.auth import get_current_user
    
    # Find candidate and user
    candidate = db_session.query(Candidate).first()
    user = db_session.query(User).filter(User.id == candidate.user_id).first()
    
    # Override dependencies
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    
    client = TestClient(app)
    
    try:
        # 1. Test when there is no ResumeAIAnalysis at all
        response = client.get("/api/v1/resume/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_status"]["created_at"] is None
        assert data["analysis_status"]["source_type"] == "GEMINI"
        
        # 2. Test when ResumeAIAnalysis exists but created_at is None
        analysis = ResumeAIAnalysis(
            candidate_id=candidate.id,
            source_type="FALLBACK",
            confidence_score="MEDIUM",
            raw_response="{}",
            parsed_json={}
        )
        db_session.add(analysis)
        db_session.commit()
        
        # Force created_at to None to test the null-handling code path
        db_session.query(ResumeAIAnalysis).filter(ResumeAIAnalysis.id == analysis.id).update({"created_at": None})
        db_session.commit()
        db_session.refresh(analysis)
        
        response = client.get("/api/v1/resume/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_status"]["created_at"] is None
        assert data["analysis_status"]["source_type"] == "FALLBACK"
        
        # 3. Test when ResumeAIAnalysis exists and created_at is set
        from datetime import datetime
        analysis.created_at = datetime(2026, 6, 24, 12, 0, 0)
        db_session.commit()
        
        response = client.get("/api/v1/resume/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_status"]["created_at"] == "2026-06-24T12:00:00"
        assert data["analysis_status"]["source_type"] == "FALLBACK"
        
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

