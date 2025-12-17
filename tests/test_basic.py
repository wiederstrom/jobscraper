"""
Basic tests to verify the setup is working
"""

import pytest
from app.config import settings
from app.db.models import Job, IrrelevantJob, SyncState


def test_config_loading():
    """Test that configuration loads correctly"""
    assert settings.database_url is not None
    assert settings.finn_location == "2.20001.22046.20220"
    assert settings.nav_county == "VESTLAND"
    assert len(settings.get_keywords()) > 0


def test_keywords_default():
    """Test that default keywords are loaded"""
    keywords = settings.get_keywords()
    assert "python" in keywords
    assert "data scientist" in keywords
    assert "machine learning" in keywords


def test_api_endpoints(client):
    """Test basic API endpoints"""
    # Test root endpoint
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Job Scraper API"
    assert data["version"] == "1.0.0"

    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "ai_enabled" in data


def test_database_models(db_session):
    """Test database models can be created"""
    # Create a job
    job = Job(
        title="Test Job",
        company="Test Company",
        url="https://test.com/job/1",
        source="FINN",
        keywords="python"
    )
    db_session.add(job)
    db_session.commit()

    # Query it back
    saved_job = db_session.query(Job).filter_by(url="https://test.com/job/1").first()
    assert saved_job is not None
    assert saved_job.title == "Test Job"
    assert saved_job.company == "Test Company"
    assert saved_job.source == "FINN"


def test_irrelevant_jobs_table(db_session):
    """Test irrelevant jobs table"""
    irrelevant = IrrelevantJob(url="https://test.com/irrelevant/1")
    db_session.add(irrelevant)
    db_session.commit()

    saved = db_session.query(IrrelevantJob).filter_by(url="https://test.com/irrelevant/1").first()
    assert saved is not None


def test_sync_state_table(db_session):
    """Test sync state table"""
    from datetime import datetime

    sync = SyncState(
        source="FINN",
        last_sync=datetime.now(),
        jobs_added_last_run=10
    )
    db_session.add(sync)
    db_session.commit()

    saved = db_session.query(SyncState).filter_by(source="FINN").first()
    assert saved is not None
    assert saved.jobs_added_last_run == 10
