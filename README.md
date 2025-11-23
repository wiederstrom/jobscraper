# Job Scraper for Data Science Positions

A Python-based web scraper that monitors **FINN.no** and **NAV.no** (Arbeidsplassen) for data science and tech job postings in Bergen, Norway.

## Features

- Scrapes job listings from FINN.no and NAV.no based on customizable keywords
- Uses **PostgreSQL** database for reliable cloud deployment
- Dashboard-ready with user interaction columns (favorites, hidden jobs, application tracking)
- Prevents duplicate entries
- Detailed logging for debugging
- Cloud-ready deployment (GitHub Actions + GCP + Railway)

## Architecture

**Recommended Production Setup:**
- **Scraper**: GitHub Actions (free scheduled runs)
- **Database**: GCP Cloud SQL PostgreSQL (persistent, shared)
- **Dashboard**: Railway (web app connected to same database)

## Installation

### Local Development

1. Clone this repository:
```bash
git clone <your-repo-url>
cd job_scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up a local PostgreSQL database:
```bash
# Install PostgreSQL (macOS)
brew install postgresql

# Start PostgreSQL
brew services start postgresql

# Create database
createdb jobsdb_local
```

4. Create `.env` file:
```bash
cp .env.example .env
# Edit .env and set DATABASE_URL to your local PostgreSQL
# DATABASE_URL=postgresql://user:pass@localhost:5432/jobsdb_local
```

5. Run the scraper locally:
```bash
python scraper.py
```

## Deployment Guide

### 1. Set Up PostgreSQL Database on GCP

1. Go to [GCP Cloud SQL](https://console.cloud.google.com/sql)
2. Create a new PostgreSQL instance:
   - Choose PostgreSQL 15
   - Region: europe-north1 (or your preferred region)
   - Machine type: Shared core (for low cost)
   - Storage: 10 GB SSD
3. Create a database named `jobsdb`
4. Create a user with a strong password
5. Note your connection details:
   - Public IP address
   - Database name
   - Username
   - Password

6. Get your connection string:
```
postgresql://username:password@PUBLIC_IP:5432/jobsdb
```

7. Allow connections from GitHub Actions:
   - Go to "Connections" → "Networking"
   - Add authorized network: `0.0.0.0/0` (GitHub Actions IPs)
   - Or use Cloud SQL Proxy for better security

### 2. Configure GitHub Actions

1. Push your code to GitHub

2. Go to your repository → Settings → Secrets and variables → Actions

3. Add these secrets:
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `FINN_LOCATION`: `2.20001.22046.20220` (Bergen)
   - `MAX_JOBS_PER_KEYWORD`: `5`
   - `KEYWORDS`: Comma-separated keywords (or leave empty for defaults)

4. The scraper will run automatically:
   - Daily at 7 AM and 5 PM UTC (8 AM and 6 PM Oslo time in winter)
   - You can trigger it manually from Actions tab

### 3. Deploy Dashboard to Railway

1. Go to [Railway.app](https://railway.app)

2. Create a new project → Deploy from GitHub

3. Select your repository

4. Add environment variable:
   - `DATABASE_URL`: Same PostgreSQL connection string from GCP

5. Your dashboard will connect to the same database as the scraper

### Database Schema

The `jobs` table includes these columns for dashboard functionality:

**Job Data:**
- `id`, `title`, `company`, `location`, `url`, `source`, `keywords`
- `deadline`, `job_type`, `published`, `scraped_date`, `description`

**User Interaction:**
- `is_hidden` - Hide irrelevant jobs
- `is_favorite` - Mark favorite jobs
- `applied` - Track application status
- `applied_date` - When you applied
- `notes` - Personal notes about the job

## Configuration

### Environment Variables

Create a `.env` file or set these in your deployment platform:

```bash
# Database (REQUIRED)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Scraper settings (optional)
FINN_LOCATION=2.20001.22046.20220
MAX_JOBS_PER_KEYWORD=5
KEYWORDS=python,sql,machine learning
LOG_LEVEL=INFO
```

The scraper requires a PostgreSQL database. `DATABASE_URL` must be set or the application will not start.

### Customizing Keywords

Edit [config.py](config.py) or set the `KEYWORDS` environment variable:

```bash
export KEYWORDS="python,sql,machine learning,data scientist"
```

## Local Usage

### Run Scraper Locally

Make sure your `.env` file has a valid `DATABASE_URL`:

```bash
python scraper.py
```

### View Jobs

```bash
# Connect to database
psql $DATABASE_URL

# View recent jobs
SELECT title, company, is_favorite, applied FROM jobs ORDER BY scraped_date DESC LIMIT 10;

# Or use one-liner
psql $DATABASE_URL -c "SELECT title, company, is_favorite, applied FROM jobs LIMIT 10;"
```

## Dashboard Integration

Your dashboard can query jobs with filters:

```python
import config

conn = config.get_database_connection()
cursor = conn.cursor()

# Get non-hidden jobs
cursor.execute("""
    SELECT * FROM jobs
    WHERE is_hidden = FALSE
    ORDER BY scraped_date DESC
""")

# Get favorites
cursor.execute("SELECT * FROM jobs WHERE is_favorite = TRUE")

# Get jobs you applied to
cursor.execute("SELECT * FROM jobs WHERE applied = TRUE")
```

## Monitoring

### Check GitHub Actions

Go to your repo → Actions tab to see scraper runs and logs

### Check Database

```bash
# Count total jobs
psql $DATABASE_URL -c "SELECT COUNT(*) FROM jobs;"

# Recent jobs
psql $DATABASE_URL -c "SELECT title, company, scraped_date FROM jobs ORDER BY scraped_date DESC LIMIT 5;"
```

## Troubleshooting

### Scraper not finding jobs

- Check if FINN.no or NAV.no HTML structure changed
- Verify network connectivity
- Check GitHub Actions logs for errors

### Database connection errors

- Verify `DATABASE_URL` format is correct
- Check GCP firewall allows connections
- Ensure database user has proper permissions

### GitHub Actions failing

- Check secrets are set correctly
- Verify requirements.txt includes all dependencies
- Review workflow logs in Actions tab

## Cost Estimate

**GitHub Actions**: Free (2,000 minutes/month for private repos)
**GCP Cloud SQL**: ~$10-30/month (Shared core PostgreSQL)
**Railway**: Free tier available, ~$5-10/month for basic hosting

Total: **~$15-40/month** for production setup

## Legal Notice

This scraper is for personal use only. Please:
- Respect website terms of service
- Implement rate limiting (already included)
- Use data responsibly
- Don't overload servers

## License

MIT License - feel free to modify and use as needed.
