"""
Pytest configuration and fixtures
"""

import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment variables before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["ANTHROPIC_API_KEY"] = "test-key"

from app.db.models import Base


# Test database URL (use SQLite for testing)
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override"""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.dependencies import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_job_data():
    """Sample job data for testing"""
    return {
        "title": "Senior Data Engineer",
        "company": "Test Company AS",
        "location": "Bergen",
        "url": "https://example.com/job/123",
        "source": "FINN",
        "keywords": "data engineer",
        "deadline": "31. desember 2024",
        "job_type": "Fast",
        "description": "We are looking for a talented data engineer...",
    }
