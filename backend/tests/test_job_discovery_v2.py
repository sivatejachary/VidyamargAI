import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.job_discovery.normalizer.normalizer import JobNormalizer
from app.job_discovery.validator.validator import JobValidator
from app.job_discovery.deduplicator.deduplicator import JobDeduplicator
from app.job_discovery.persistence.manager import JobPersistenceManager
from app.job_discovery.events.dispatcher import JobEventDispatcher

def test_job_normalization():
    normalizer = JobNormalizer()
    raw = {
        "title": "Software Engineer  ",
        "company_name": "TestCompany ",
        "description": "Short description",
        "apply_url": "http://example.com/apply",
        "location": "Remote",
        "is_remote": True,
        "salary_min": 100000,
        "salary_max": 150000,
        "experience_min_years": 2,
        "experience_max_years": 5,
        "source_name": "remoteok"
    }
    res = normalizer.normalize(raw)
    assert res["title"] == "Software Engineer"
    assert res["company_name"] == "TestCompany"
    assert res["title_normalized"] == "software engineer"
    assert res["is_remote"] is True
    assert res["lifecycle_status"] == "normalized"

def test_job_validation():
    validator = JobValidator()
    
    # Valid job
    valid_job = {"title": "Full Stack Dev", "company_name": "Google", "description": "Good job details"}
    assert validator.validate(valid_job) is None

    # Invalid title
    invalid_title = {"title": "A", "company_name": "Google", "description": "Good job details"}
    assert validator.validate(invalid_title) == "invalid_title"

    # Spam job
    spam_job = {"title": "Work From Home Data Entry clerk", "company_name": "Google", "description": "data entry and copy paste work"}
    assert validator.validate(spam_job) == "spam"

@pytest.mark.asyncio
async def test_event_dispatcher():
    with patch("app.job_discovery.events.dispatcher.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock(return_value="mock-msg-id")
        
        dispatcher = JobEventDispatcher()
        await dispatcher.publish_persisted(job_id=999, title="Eng", company="Alpha")
        
        mock_bus.publish.assert_called_once_with(
            "jobs.persisted.v1",
            {
                "job_id": 999,
                "title": "Eng",
                "company": "Alpha",
                "lifecycle_status": "persisted"
            }
        )
