"""
Unit tests for repository layer
"""

import pytest
from datetime import datetime, timedelta

from app.db.models import Job, IrrelevantJob, SyncState
from app.db.repositories.job_repository import JobRepository
from app.db.repositories.irrelevant_repository import IrrelevantJobRepository
from app.db.repositories.sync_state_repository import SyncStateRepository


class TestJobRepository:
    """Tests for JobRepository"""

    def test_create_job(self, db_session):
        """Test creating a job"""
        repo = JobRepository(db_session)

        job_data = {
            "title": "Data Engineer",
            "company": "Test AS",
            "url": "https://test.com/job/1",
            "source": "FINN",
            "keywords": "data engineer",
        }

        job = repo.create(job_data)

        assert job.id is not None
        assert job.title == "Data Engineer"
        assert job.company == "Test AS"
        assert job.source == "FINN"

    def test_get_by_url(self, db_session):
        """Test getting job by URL"""
        repo = JobRepository(db_session)

        # Create job
        job_data = {
            "title": "Python Developer",
            "company": "Dev Company",
            "url": "https://test.com/python-dev",
            "source": "NAV",
            "keywords": "python",
        }
        created = repo.create(job_data)

        # Retrieve by URL
        found = repo.get_by_url("https://test.com/python-dev")

        assert found is not None
        assert found.id == created.id
        assert found.title == "Python Developer"

    def test_exists_by_url(self, db_session):
        """Test checking if job exists by URL"""
        repo = JobRepository(db_session)

        repo.create({
            "title": "Test Job",
            "company": "Test",
            "url": "https://exists.com/job",
            "source": "FINN",
            "keywords": "test",
        })

        assert repo.exists_by_url("https://exists.com/job") is True
        assert repo.exists_by_url("https://notexists.com/job") is False

    def test_get_all_with_filters_by_source(self, db_session):
        """Test filtering jobs by source"""
        repo = JobRepository(db_session)

        # Create FINN and NAV jobs
        repo.create({
            "title": "FINN Job",
            "company": "Company A",
            "url": "https://test.com/1",
            "source": "FINN",
            "keywords": "test",
        })
        repo.create({
            "title": "NAV Job",
            "company": "Company B",
            "url": "https://test.com/2",
            "source": "NAV",
            "keywords": "test",
        })

        finn_jobs = repo.get_all_with_filters(source="FINN")
        nav_jobs = repo.get_all_with_filters(source="NAV")

        assert len(finn_jobs) == 1
        assert len(nav_jobs) == 1
        assert finn_jobs[0].source == "FINN"
        assert nav_jobs[0].source == "NAV"

    def test_get_all_with_filters_by_search(self, db_session):
        """Test searching jobs"""
        repo = JobRepository(db_session)

        repo.create({
            "title": "Senior Python Developer",
            "company": "Tech Corp",
            "url": "https://test.com/1",
            "source": "FINN",
            "keywords": "python",
            "description": "We need a Python expert",
        })
        repo.create({
            "title": "Java Developer",
            "company": "Java Corp",
            "url": "https://test.com/2",
            "source": "FINN",
            "keywords": "java",
            "description": "Java programming required",
        })

        python_jobs = repo.get_all_with_filters(search="Python")
        java_jobs = repo.get_all_with_filters(search="Java")

        assert len(python_jobs) == 1
        assert len(java_jobs) == 1
        assert "Python" in python_jobs[0].title

    def test_get_all_with_filters_exclude_hidden(self, db_session):
        """Test that hidden jobs are excluded by default"""
        repo = JobRepository(db_session)

        repo.create({
            "title": "Visible Job",
            "company": "Company",
            "url": "https://test.com/1",
            "source": "FINN",
            "keywords": "test",
            "is_hidden": False,
        })
        repo.create({
            "title": "Hidden Job",
            "company": "Company",
            "url": "https://test.com/2",
            "source": "FINN",
            "keywords": "test",
            "is_hidden": True,
        })

        visible_jobs = repo.get_all_with_filters()

        assert len(visible_jobs) == 1
        assert visible_jobs[0].title == "Visible Job"

    def test_update_job_metadata(self, db_session):
        """Test updating job metadata"""
        repo = JobRepository(db_session)

        job = repo.create({
            "title": "Test Job",
            "company": "Company",
            "url": "https://test.com/1",
            "source": "FINN",
            "keywords": "test",
        })

        # Update metadata
        updated = repo.update_job_metadata(
            job.id,
            is_favorite=True,
            applied=True,
            notes="Interesting position"
        )

        assert updated.is_favorite is True
        assert updated.applied is True
        assert updated.applied_date is not None
        assert updated.notes == "Interesting position"

    def test_update_job_metadata_unapply(self, db_session):
        """Test un-applying removes applied_date"""
        repo = JobRepository(db_session)

        job = repo.create({
            "title": "Test Job",
            "company": "Company",
            "url": "https://test.com/1",
            "source": "FINN",
            "keywords": "test",
        })

        # Apply first
        repo.update_job_metadata(job.id, applied=True)

        # Then unapply
        updated = repo.update_job_metadata(job.id, applied=False)

        assert updated.applied is False
        assert updated.applied_date is None

    def test_get_statistics(self, db_session):
        """Test getting job statistics"""
        repo = JobRepository(db_session)

        # Create various jobs
        repo.create({
            "title": "FINN Job",
            "company": "Company",
            "url": "https://test.com/1",
            "source": "FINN",
            "keywords": "test",
            "is_favorite": True,
        })
        repo.create({
            "title": "NAV Job",
            "company": "Company",
            "url": "https://test.com/2",
            "source": "NAV",
            "keywords": "test",
            "applied": True,
        })

        stats = repo.get_statistics()

        assert stats["total_jobs"] == 2
        assert stats["favorites"] == 1
        assert stats["applied"] == 1
        assert stats["sources"]["FINN"] == 1
        assert stats["sources"]["NAV"] == 1

    def test_mark_as_inactive(self, db_session):
        """Test marking jobs as inactive"""
        repo = JobRepository(db_session)

        job1 = repo.create({
            "title": "Job 1",
            "company": "Company",
            "url": "https://test.com/1",
            "source": "FINN",
            "keywords": "test",
            "status": "ACTIVE",
        })
        job2 = repo.create({
            "title": "Job 2",
            "company": "Company",
            "url": "https://test.com/2",
            "source": "FINN",
            "keywords": "test",
            "status": "ACTIVE",
        })

        count = repo.mark_as_inactive([job1.id, job2.id])

        assert count == 2

        # Verify status changed
        updated1 = repo.get_by_id(job1.id)
        updated2 = repo.get_by_id(job2.id)

        assert updated1.status == "INACTIVE"
        assert updated2.status == "INACTIVE"


class TestIrrelevantJobRepository:
    """Tests for IrrelevantJobRepository"""

    def test_add_irrelevant_job(self, db_session):
        """Test adding irrelevant job URL"""
        repo = IrrelevantJobRepository(db_session)

        irrelevant = repo.add("https://test.com/irrelevant")

        assert irrelevant.url == "https://test.com/irrelevant"

    def test_add_duplicate_irrelevant_job(self, db_session):
        """Test adding duplicate returns existing"""
        repo = IrrelevantJobRepository(db_session)

        first = repo.add("https://test.com/irrelevant")
        second = repo.add("https://test.com/irrelevant")

        assert first.url == second.url
        assert repo.count() == 1

    def test_exists_by_url(self, db_session):
        """Test checking if URL exists"""
        repo = IrrelevantJobRepository(db_session)

        repo.add("https://test.com/irrelevant")

        assert repo.exists_by_url("https://test.com/irrelevant") is True
        assert repo.exists_by_url("https://test.com/other") is False

    def test_remove_irrelevant_job(self, db_session):
        """Test removing irrelevant job URL"""
        repo = IrrelevantJobRepository(db_session)

        repo.add("https://test.com/irrelevant")
        assert repo.exists_by_url("https://test.com/irrelevant") is True

        removed = repo.remove("https://test.com/irrelevant")
        assert removed is True
        assert repo.exists_by_url("https://test.com/irrelevant") is False

    def test_get_all_urls(self, db_session):
        """Test getting all irrelevant URLs"""
        repo = IrrelevantJobRepository(db_session)

        repo.add("https://test.com/1")
        repo.add("https://test.com/2")
        repo.add("https://test.com/3")

        urls = repo.get_all_urls()

        assert len(urls) == 3
        assert "https://test.com/1" in urls
        assert "https://test.com/2" in urls
        assert "https://test.com/3" in urls


class TestSyncStateRepository:
    """Tests for SyncStateRepository"""

    def test_create_sync_state(self, db_session):
        """Test creating sync state"""
        repo = SyncStateRepository(db_session)

        sync = repo.update_sync_state(
            source="FINN",
            last_sync=datetime.now(),
            jobs_added=10,
            jobs_removed=2
        )

        assert sync.source == "FINN"
        assert sync.jobs_added_last_run == 10
        assert sync.jobs_removed_last_run == 2

    def test_update_existing_sync_state(self, db_session):
        """Test updating existing sync state"""
        repo = SyncStateRepository(db_session)

        # Create initial
        first = repo.update_sync_state(
            source="NAV",
            jobs_added=5
        )

        # Update
        second = repo.update_sync_state(
            source="NAV",
            jobs_added=10
        )

        assert first.source == second.source
        assert second.jobs_added_last_run == 10
        assert repo.count() == 1  # Only one record

    def test_get_by_source(self, db_session):
        """Test getting sync state by source"""
        repo = SyncStateRepository(db_session)

        repo.update_sync_state(source="FINN", jobs_added=5)
        repo.update_sync_state(source="NAV", jobs_added=8)

        finn_sync = repo.get_by_source("FINN")
        nav_sync = repo.get_by_source("NAV")

        assert finn_sync is not None
        assert nav_sync is not None
        assert finn_sync.jobs_added_last_run == 5
        assert nav_sync.jobs_added_last_run == 8

    def test_get_last_sync_time(self, db_session):
        """Test getting last sync timestamp"""
        repo = SyncStateRepository(db_session)

        now = datetime.now()
        repo.update_sync_state(source="FINN", last_sync=now)

        last_sync = repo.get_last_sync_time("FINN")

        assert last_sync is not None
        assert abs((last_sync - now).total_seconds()) < 1

    def test_record_scrape_result(self, db_session):
        """Test recording scrape result"""
        repo = SyncStateRepository(db_session)

        result = repo.record_scrape_result(
            source="NAV",
            jobs_added=15,
            jobs_removed=3,
            etag="abc123"
        )

        assert result.jobs_added_last_run == 15
        assert result.jobs_removed_last_run == 3
        assert result.last_etag == "abc123"
        assert result.last_sync is not None
