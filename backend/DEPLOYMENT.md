# Deployment Guide - Railway

This guide walks through deploying the Job Scraper API to Railway.

## Prerequisites

1. Railway account (sign up at https://railway.app)
2. GitHub repository connected to Railway
3. PostgreSQL database (use your existing Google Cloud SQL or Railway PostgreSQL)

## Step 1: Create New Railway Project

1. Go to https://railway.app/new
2. Select "Deploy from GitHub repo"
3. Choose `wiederstrom/jobscraper` repository
4. Select the `main` branch

## Step 2: Configure Root Directory

Since the backend code is in the `backend/` directory:

1. In Railway project settings, go to **Settings**
2. Under **Build**, set **Root Directory** to: `backend`
3. Railway will automatically detect the Dockerfile

## Step 3: Add PostgreSQL Database (Optional)

If you want to use Railway's PostgreSQL instead of Google Cloud SQL:

1. Click **+ New** in your Railway project
2. Select **Database** → **PostgreSQL**
3. Railway will create a database and provide a `DATABASE_URL` environment variable automatically

**OR** use your existing Google Cloud SQL database (recommended to keep existing 61 jobs):

- Manually add `DATABASE_URL` environment variable (see Step 4)

## Step 4: Set Environment Variables

In Railway project → **Variables**, add the following:

### Required Variables

```bash
# Database (use your existing Google Cloud SQL)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@34.51.150.201:5432/jobsdb

# Anthropic API Key
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

### Optional Variables

```bash
# AI Features (enable when ready)
ENABLE_SUMMARIZATION=false
ENABLE_AI_FILTER=false
AI_MODEL=claude-3-haiku-20240307

# Location Settings
FINN_LOCATION=2.20001.22046.20220
NAV_COUNTY=VESTLAND
NAV_MUNICIPAL=VESTLAND.BERGEN

# Scraper Limits
MAX_JOBS_PER_KEYWORD=100
MAX_KEYWORDS=0

# Logging
LOG_LEVEL=INFO

# CORS Origins (add your frontend URL when deployed)
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000,http://localhost:5173
```

### Railway-Provided Variables

Railway automatically provides:
- `PORT` - The port your app should listen on
- `RAILWAY_ENVIRONMENT` - The environment name (production/staging)

## Step 5: Deploy

1. Click **Deploy** in Railway dashboard
2. Railway will:
   - Build the Docker image
   - Run database migrations (`python scripts/init_db.py`)
   - Start the application (`uvicorn app.main:app`)
3. Monitor the deployment logs for any errors

## Step 6: Get Your API URL

1. Go to **Settings** → **Networking**
2. Click **Generate Domain** to get a public URL
3. Your API will be available at: `https://your-app.railway.app`

## Step 7: Test the Deployment

Test the API endpoints:

```bash
# Health check
curl https://your-app.railway.app/api/v1/health

# Get jobs
curl https://your-app.railway.app/api/v1/jobs?limit=10

# Get statistics
curl https://your-app.railway.app/api/v1/stats
```

## Step 8: Update Frontend

Once deployed, update your frontend's `.env.production`:

```bash
VITE_API_BASE_URL=https://your-app.railway.app
```

And add the frontend URL to Railway's `CORS_ORIGINS` environment variable.

## Database Migration

The `scripts/init_db.py` script runs automatically on deployment and will:

- Add new columns (`last_checked`, `external_id`, `status`, `expire_date`) if they don't exist
- Create indexes for performance
- Create `sync_state` table if it doesn't exist
- **Preserve all existing 61 jobs** (non-destructive)

## Monitoring & Logs

View logs in Railway dashboard:
1. Click on your service
2. Go to **Deployments**
3. Click on the latest deployment
4. View **Logs** tab

## Environment-Specific Settings

### Development
- Use Railway preview deployments for testing
- Set `LOG_LEVEL=DEBUG` for verbose logging

### Production
- Set `LOG_LEVEL=INFO` or `WARNING`
- Enable AI features when ready: `ENABLE_SUMMARIZATION=true`
- Monitor database connection pool (Railway auto-scales)

## Troubleshooting

### Build Fails
- Check that `Root Directory` is set to `backend`
- Verify Dockerfile syntax
- Check build logs for Python dependency errors

### Database Connection Fails
- Verify `DATABASE_URL` is correct
- Check Google Cloud SQL allows Railway's IP addresses
- Test connection locally: `psql $DATABASE_URL`

### App Crashes on Startup
- Check environment variables are set
- Verify `DATABASE_URL` format: `postgresql://user:pass@host:port/db`
- Check deployment logs for Python import errors

### CORS Errors
- Add frontend URL to `CORS_ORIGINS` environment variable
- Format: `https://frontend.vercel.app,http://localhost:3000`
- Redeploy after changing environment variables

## Cost Estimation

Railway pricing (as of 2024):
- **Hobby Plan**: $5/month (500 hours execution time)
- **Pro Plan**: $20/month (unlimited execution time)

Your API should run fine on the Hobby plan since:
- It's a single-user app
- Scraping runs periodically (not constantly)
- Low traffic expected

## Next Steps After Deployment

1. **Test all endpoints** with your production data
2. **Deploy frontend** to Vercel/Netlify
3. **Configure scraping schedule** (Phase 9)
4. **Enable AI features** when needed
5. **Monitor performance** and adjust resources if needed

## Railway CLI (Optional)

Install Railway CLI for easier management:

```bash
# Install
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# View logs
railway logs

# Run commands in Railway environment
railway run python scripts/some_script.py
```

## Rollback

If deployment fails:
1. Go to **Deployments** tab
2. Find previous successful deployment
3. Click **⋮** → **Redeploy**

## Security Notes

- Never commit `.env` file to git (already in `.gitignore`)
- Rotate `ANTHROPIC_API_KEY` periodically
- Use Railway's secret management (variables are encrypted)
- Consider adding authentication for production (Phase 11)
- Monitor API usage and set rate limits if needed
