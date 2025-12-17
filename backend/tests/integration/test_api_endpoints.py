"""
Integration tests for API endpoints
Tests the full API with real data flow
"""

import pytest
from fastapi.testclient import TestClient


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ["healthy", "degraded"]
    assert "database" in data
    assert "ai_enabled" in data
    assert "timestamp" in data


def test_jobs_list_endpoint(client, db_session):
    """Test listing jobs"""
    from app.db.repositories.job_repository import JobRepository

    # Create some test jobs
    repo = JobRepository(db_session)
    repo.create({
        "title": "Python Developer",
        "company": "Tech Corp",
        "url": "https://example.com/job1",
        "source": "FINN",
        "keywords": "python",
    })
    repo.create({
        "title": "Data Engineer",
        "company": "Data Inc",
        "url": "https://example.com/job2",
        "source": "NAV",
        "keywords": "data engineer",
    })

    # Get all jobs
    response = client.get("/api/v1/jobs")

    assert response.status_code == 200
    data = response.json()

    assert "jobs" in data
    assert "total" in data
    assert len(data["jobs"]) == 2
    assert data["total"] >= 2


def test_jobs_filter_by_source(client, db_session):
    """Test filtering jobs by source"""
    from app.db.repositories.job_repository import JobRepository

    repo = JobRepository(db_session)
    repo.create({
        "title": "FINN Job",
        "company": "Company A",
        "url": "https://example.com/finn1",
        "source": "FINN",
        "keywords": "test",
    })
    repo.create({
        "title": "NAV Job",
        "company": "Company B",
        "url": "https://example.com/nav1",
        "source": "NAV",
        "keywords": "test",
    })

    # Filter by FINN
    response = client.get("/api/v1/jobs?source=FINN")
    data = response.json()

    assert response.status_code == 200
    assert all(job["source"] == "FINN" for job in data["jobs"])


def test_jobs_search(client, db_session):
    """Test searching jobs"""
    from app.db.repositories.job_repository import JobRepository

    repo = JobRepository(db_session)
    repo.create({
        "title": "Senior Python Developer",
        "company": "Python Corp",
        "url": "https://example.com/search1",
        "source": "FINN",
        "keywords": "python",
        "description": "We need a Python expert"
    })
    repo.create({
        "title": "Java Developer",
        "company": "Java Corp",
        "url": "https://example.com/search2",
        "source": "FINN",
        "keywords": "java",
        "description": "Java programming required"
    })

    # Search for Python
    response = client.get("/api/v1/jobs?search=Python")
    data = response.json()

    assert response.status_code == 200
    assert len(data["jobs"]) == 1
    assert "Python" in data["jobs"][0]["title"]


def test_get_single_job(client, db_session):
    """Test getting a single job by ID"""
    from app.db.repositories.job_repository import JobRepository

    repo = JobRepository(db_session)
    job = repo.create({
        "title": "Test Job",
        "company": "Test Company",
        "url": "https://example.com/single",
        "source": "FINN",
        "keywords": "test",
        "description": "Full description here"
    })

    # Get job by ID
    response = client.get(f"/api/v1/jobs/{job.id}")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == job.id
    assert data["title"] == "Test Job"
    assert data["description"] == "Full description here"


def test_get_nonexistent_job(client):
    """Test getting a job that doesn't exist"""
    response = client.get("/api/v1/jobs/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_job_metadata(client, db_session):
    """Test updating job metadata"""
    from app.db.repositories.job_repository import JobRepository

    repo = JobRepository(db_session)
    job = repo.create({
        "title": "Update Test",
        "company": "Company",
        "url": "https://example.com/update",
        "source": "FINN",
        "keywords": "test",
    })

    # Update to favorite and applied
    response = client.patch(f"/api/v1/jobs/{job.id}", json={
        "is_favorite": True,
        "applied": True,
        "notes": "Very interesting position"
    })

    assert response.status_code == 200
    data = response.json()

    assert data["is_favorite"] is True
    assert data["applied"] is True
    assert data["applied_date"] is not None
    assert data["notes"] == "Very interesting position"


def test_hide_job(client, db_session):
    """Test soft deleting (hiding) a job"""
    from app.db.repositories.job_repository import JobRepository

    repo = JobRepository(db_session)
    job = repo.create({
        "title": "Hide Test",
        "company": "Company",
        "url": "https://example.com/hide",
        "source": "FINN",
        "keywords": "test",
    })

    # Hide the job
    response = client.delete(f"/api/v1/jobs/{job.id}")

    assert response.status_code == 200
    assert "hidden" in response.json()["message"].lower()

    # Verify it's hidden (shouldn't appear in default list)
    list_response = client.get("/api/v1/jobs")
    jobs = list_response.json()["jobs"]

    assert not any(j["id"] == job.id for j in jobs)


def test_statistics_endpoint(client, db_session):
    """Test statistics endpoint"""
    from app.db.repositories.job_repository import JobRepository

    repo = JobRepository(db_session)

    # Create test data
    repo.create({
        "title": "Job 1",
        "company": "Company",
        "url": "https://example.com/stat1",
        "source": "FINN",
        "keywords": "test",
        "is_favorite": True,
    })
    repo.create({
        "title": "Job 2",
        "company": "Company",
        "url": "https://example.com/stat2",
        "source": "NAV",
        "keywords": "test",
        "applied": True,
    })

    # Get statistics
    response = client.get("/api/v1/stats")

    assert response.status_code == 200
    data = response.json()

    assert "total_jobs" in data
    assert "favorites" in data
    assert "applied" in data
    assert "sources" in data
    assert "status" in data
    assert "new_last_7_days" in data

    assert data["favorites"] >= 1
    assert data["applied"] >= 1
    assert data["sources"]["FINN"] >= 1
    assert data["sources"]["NAV"] >= 1


def test_pagination(client, db_session):
    """Test pagination parameters"""
    from app.db.repositories.job_repository import JobRepository

    repo = JobRepository(db_session)

    # Create 10 jobs
    for i in range(10):
        repo.create({
            "title": f"Job {i}",
            "company": "Company",
            "url": f"https://example.com/page{i}",
            "source": "FINN",
            "keywords": "test",
        })

    # Get first page (5 items)
    response = client.get("/api/v1/jobs?limit=5&skip=0")
    data = response.json()

    assert response.status_code == 200
    assert len(data["jobs"]) == 5
    assert data["limit"] == 5
    assert data["skip"] == 0

    # Get second page
    response = client.get("/api/v1/jobs?limit=5&skip=5")
    data = response.json()

    assert response.status_code == 200
    assert len(data["jobs"]) == 5
    assert data["skip"] == 5
