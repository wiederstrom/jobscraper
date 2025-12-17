# Job Scraper API

A production-ready FastAPI application for scraping Norwegian job postings from FINN.no and NAV.no with AI-powered filtering and summarization.

## Features

- 🔍 **Dual-source scraping**: FINN.no (web scraping) + NAV.no (official API)
- 🤖 **AI-powered**: Claude AI for relevancy filtering and Norwegian summaries
- 📊 **RESTful API**: Clean FastAPI endpoints for React frontend
- 🐳 **Docker-ready**: Containerized for easy deployment
- ⏰ **Automated scraping**: Background jobs running 2x daily
- 🧹 **Auto-cleanup**: Removes inactive/expired job listings
- 📦 **Type-safe**: Pydantic schemas with full validation
- 🏗️ **Clean architecture**: Layered design with repository pattern

## Project Structure

```
job-scraper-api/
├── app/
│   ├── api/              # API endpoints
│   ├── core/             # Business logic (scrapers, AI, job management)
│   ├── db/               # Database models and repositories
│   ├── schemas/          # Pydantic request/response models
│   ├── tasks/            # Background jobs
│   ├── utils/            # Utilities and constants
│   ├── config.py         # Configuration management
│   └── main.py           # FastAPI application
├── old/                  # Archived prototype code
├── scripts/              # Utility scripts
├── tests/                # Test suite
├── alembic/              # Database migrations
├── Dockerfile            # Production container
├── docker-compose.yml    # Local development
└── requirements.txt      # Python dependencies
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (optional)
- Anthropic API key
- NAV API token (register at https://navikt.github.io/pam-stilling-feed/)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd job_scraper
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Initialize database**
   ```bash
   python scripts/init_db.py
   ```

6. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

Visit http://localhost:8000/docs for interactive API documentation.

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## Configuration

All configuration is managed through environment variables:

### Required

- `DATABASE_URL` - PostgreSQL connection string
- `ANTHROPIC_API_KEY` - Claude API key
- `NAV_API_TOKEN` - NAV API JWT bearer token

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `FINN_LOCATION` | `2.20001.22046.20220` | FINN location code (Bergen) |
| `NAV_COUNTY` | `VESTLAND` | NAV county filter |
| `NAV_MUNICIPAL` | `VESTLAND.BERGEN` | NAV municipality filter |
| `MAX_JOBS_PER_KEYWORD` | `100` | Jobs to fetch per keyword |
| `MAX_KEYWORDS` | `0` | Keyword limit (0 = all) |
| `ENABLE_SUMMARIZATION` | `false` | Enable AI summaries |
| `ENABLE_AI_FILTER` | `false` | Enable AI filtering |
| `AI_MODEL` | `claude-3-haiku-20240307` | Claude model |
| `LOG_LEVEL` | `INFO` | Logging level |

## API Endpoints

### Base URL: `/api/v1`

#### Health Check
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed system status

#### Jobs (Coming in Phase 2)
- `GET /jobs` - List jobs with filters
- `GET /jobs/{id}` - Get job details
- `PATCH /jobs/{id}` - Update job
- `DELETE /jobs/{id}` - Hide job

#### Statistics (Coming in Phase 2)
- `GET /stats` - Job statistics

## Database Schema

### Jobs Table
```sql
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    url TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    keywords TEXT,
    deadline TEXT,
    job_type TEXT,
    published TEXT,
    scraped_date TIMESTAMP NOT NULL,
    description TEXT,
    summary TEXT,
    is_hidden BOOLEAN DEFAULT FALSE,
    is_favorite BOOLEAN DEFAULT FALSE,
    applied BOOLEAN DEFAULT FALSE,
    applied_date TIMESTAMP,
    notes TEXT,
    last_checked TIMESTAMP,
    external_id TEXT,
    status TEXT DEFAULT 'ACTIVE',
    expire_date TIMESTAMP
);
```

## Deployment

### Railway

1. **Create new project** on Railway
2. **Add PostgreSQL database** plugin
3. **Connect GitHub repository**
4. **Set environment variables** (see Configuration section)
5. **Deploy**

Railway will automatically:
- Build the Docker image
- Run database migrations
- Start the application
- Set up health checks

### Manual Deployment

```bash
# Build Docker image
docker build -t job-scraper-api .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=your_db_url \
  -e ANTHROPIC_API_KEY=your_key \
  -e NAV_API_TOKEN=your_token \
  job-scraper-api
```

## Development Roadmap

### ✅ Phase 1: Foundation (COMPLETED)
- [x] Project structure
- [x] SQLAlchemy models
- [x] Database session management
- [x] Pydantic configuration
- [x] Docker setup
- [x] Basic FastAPI app

### 🚧 Phase 2: Repository Layer (Next)
- [ ] Base repository pattern
- [ ] Job repository
- [ ] Irrelevant job repository
- [ ] Unit tests

### 📋 Upcoming Phases
- Phase 3: Pydantic schemas & FastAPI endpoints
- Phase 4: Core API implementation
- Phase 5: FINN scraper refactor
- Phase 6: NAV API integration
- Phase 7: AI services refactor
- Phase 8: Job manager orchestration
- Phase 9: Background jobs & scheduling
- Phase 10: Cleanup feature
- Phase 11: Production deployment
- Phase 12: Testing & documentation

See `.claude/plans/snazzy-wobbling-pinwheel.md` for detailed implementation plan.

## Migration Notes

This is a complete refactor of the original prototype job scraper. Key improvements:

- **Clean architecture** with proper separation of concerns
- **Repository pattern** for data access abstraction
- **Pydantic Settings** for type-safe configuration
- **FastAPI** for modern async API
- **NAV official API** instead of web scraping
- **Background jobs** with APScheduler
- **Docker containerization** for consistent deployment
- **Comprehensive testing** (coming in Phase 12)

Original code is preserved in `old/` directory.

## Testing

Run tests with pytest:

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## License

MIT License

## Support

For issues and questions, please create an issue on GitHub.
