# Testing Guide

## Quick Testing Options

### Option 1: Run All Tests with Pytest ✅ RECOMMENDED

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_basic.py -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=html

# Run only tests matching a pattern
pytest tests/ -k "test_config" -v
```

**All 6 tests passed successfully! ✅**

### Option 2: Start the FastAPI Server

```bash
# Option A: Use the run script
python scripts/run_server.py

# Option B: Direct uvicorn
uvicorn app.main:app --reload

# Option C: Python directly
python -m app.main
```

Then visit:
- **Interactive API docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health
- **Root endpoint**: http://localhost:8000/

### Option 3: Manual Python Tests

```bash
# Quick configuration check
python -c "from app.config import settings; print(f'✅ Config loaded: {len(settings.get_keywords())} keywords')"

# Database connection test
python -c "from app.db.session import get_db_context; from app.db.models import Job; \
with get_db_context() as db: print(f'✅ Database: {db.query(Job).count()} jobs')"

# FastAPI app test
python -c "from app.main import app; print(f'✅ FastAPI: {app.title} v{app.version}')"
```

### Option 4: Docker Testing

```bash
# Start all services (API + PostgreSQL)
docker-compose up -d

# View logs
docker-compose logs -f api

# Test the API
curl http://localhost:8000/health

# Stop services
docker-compose down
```

## Test Results Summary

### ✅ Completed Tests

1. **test_config_loading** - Configuration loads correctly from .env
2. **test_keywords_default** - All 41 default keywords present
3. **test_api_endpoints** - Both `/` and `/health` endpoints working
4. **test_database_models** - Job model CRUD operations work
5. **test_irrelevant_jobs_table** - Irrelevant jobs table functional
6. **test_sync_state_table** - Sync state table functional

### Database Status

- **Total jobs**: 61
- **Tables**: jobs, irrelevant_jobs, sync_state
- **New columns added**: last_checked, external_id, status, expire_date
- **Indexes created**: 5 performance indexes

### API Endpoints Available

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

## Quick Start for Development

```bash
# 1. Activate virtual environment
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# 2. Install dependencies (if not already done)
pip install -r requirements.txt

# 3. Run tests to verify setup
pytest tests/test_basic.py -v

# 4. Start development server
python scripts/run_server.py

# 5. Open browser to http://localhost:8000/docs
```

## Manual API Testing with curl

```bash
# Test root endpoint
curl http://localhost:8000/

# Test health endpoint
curl http://localhost:8000/health

# Pretty print JSON
curl http://localhost:8000/health | python -m json.tool
```

## Running Individual Tests

```bash
# Test just configuration
pytest tests/test_basic.py::test_config_loading -v

# Test just API endpoints
pytest tests/test_basic.py::test_api_endpoints -v

# Test just database
pytest tests/test_basic.py::test_database_models -v
```

## Troubleshooting

### If tests fail with database errors:
```bash
# Run database initialization
python scripts/init_db.py
```

### If imports fail:
```bash
# Make sure you're in the project root
pwd  # Should show: /Users/erik/Documents/GitHub/job_scraper

# Install dependencies
pip install -r requirements.txt
```

### If port 8000 is already in use:
```bash
# Find process using port 8000
lsof -ti:8000

# Kill it
kill -9 $(lsof -ti:8000)

# Or use a different port
uvicorn app.main:app --port 8001
```

## Next Steps

After verifying everything works:
1. ✅ Phase 1 complete - Foundation & Setup
2. 🚧 Phase 2 next - Repository Layer
3. Continue with the migration plan
