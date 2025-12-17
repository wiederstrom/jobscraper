"""
Database initialization script
Creates tables if they don't exist and adds new columns/indexes
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from app.db.session import engine, SessionLocal
from app.db.models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize database with schema updates"""

    logger.info("Starting database initialization...")

    with SessionLocal() as db:
        try:
            # Add new columns to existing jobs table if they don't exist
            logger.info("Adding new columns to jobs table...")

            alter_statements = [
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS last_checked TIMESTAMP",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS external_id TEXT",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ACTIVE'",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS expire_date TIMESTAMP",
            ]

            for statement in alter_statements:
                try:
                    db.execute(text(statement))
                    db.commit()
                    logger.info(f"Executed: {statement}")
                except Exception as e:
                    logger.warning(f"Column may already exist: {e}")
                    db.rollback()

            # Create indexes
            logger.info("Creating indexes...")

            index_statements = [
                "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)",
                "CREATE INDEX IF NOT EXISTS idx_jobs_scraped_date ON jobs(scraped_date DESC)",
                "CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)",
                "CREATE INDEX IF NOT EXISTS idx_jobs_external_id ON jobs(external_id)",
                "CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url)",
            ]

            for statement in index_statements:
                try:
                    db.execute(text(statement))
                    db.commit()
                    logger.info(f"Executed: {statement}")
                except Exception as e:
                    logger.warning(f"Index may already exist: {e}")
                    db.rollback()

            # Create sync_state table if it doesn't exist
            logger.info("Creating sync_state table...")

            sync_state_sql = """
            CREATE TABLE IF NOT EXISTS sync_state (
                source TEXT PRIMARY KEY,
                last_sync TIMESTAMP NOT NULL,
                last_etag TEXT,
                jobs_added_last_run INTEGER DEFAULT 0,
                jobs_removed_last_run INTEGER DEFAULT 0
            )
            """

            db.execute(text(sync_state_sql))
            db.commit()
            logger.info("sync_state table created/verified")

            # Verify existing tables
            logger.info("Verifying existing tables...")

            result = db.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))

            tables = [row[0] for row in result]
            logger.info(f"Found tables: {', '.join(tables)}")

            logger.info("✅ Database initialization complete!")

        except Exception as e:
            logger.error(f"❌ Error initializing database: {e}")
            raise


if __name__ == "__main__":
    init_database()
