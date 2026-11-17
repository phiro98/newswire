import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

logger = logging.getLogger(__name__)

# Resolve connection parameters based on dialect
connect_args = {}
engine_kwargs = {"pool_pre_ping": True}

db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    # Ensure directory exists for sqlite file
    db_path = db_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
else:
    # PostgreSQL pooling optimization
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 1800,
    })

engine = create_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs
)

# Enable WAL mode for SQLite to support concurrent reading/writing
if db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI Dependency for database session management."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes database schema and bootstraps default sources if empty."""
    from app.models import NewsSource
    Base.metadata.create_all(bind=engine)

    # Seed default sources if table is empty
    with SessionLocal() as db:
        existing_count = db.query(NewsSource).count()
        if existing_count == 0:
            logger.info("Database is empty. Seeding initial authoritative news & compliance sources...")
            default_sources = [
                NewsSource(
                    name="Reuters World News",
                    url="https://feeds.bbci.co.uk/news/world/rss.xml",
                    source_type="rss",
                    category="Global Politics & Affairs",
                    fetch_interval_minutes=15,
                    is_active=True
                ),
                NewsSource(
                    name="BBC Business News",
                    url="https://feeds.bbci.co.uk/news/business/rss.xml",
                    source_type="rss",
                    category="Business & Economy",
                    fetch_interval_minutes=15,
                    is_active=True
                ),
                NewsSource(
                    name="SEC Press Releases & Regulatory",
                    url="https://www.sec.gov/news/pressreleases.rss",
                    source_type="rss",
                    category="Regulatory & Compliance",
                    fetch_interval_minutes=30,
                    is_active=True
                ),
                NewsSource(
                    name="Hacker News Top Stories",
                    url="https://news.ycombinator.com/rss",
                    source_type="rss",
                    category="Cybersecurity & Tech",
                    fetch_interval_minutes=30,
                    is_active=True
                ),
                NewsSource(
                    name="Google News - Compliance & Sanctions",
                    url="https://news.google.com/rss/search?q=sanctions+OR+anti-money+laundering+OR+bribery+investigation&hl=en-US&gl=US&ceid=US:en",
                    source_type="rss",
                    category="Compliance & Enforcement",
                    fetch_interval_minutes=20,
                    is_active=True
                )
            ]
            db.add_all(default_sources)
            db.commit()
            logger.info(f"Successfully seeded {len(default_sources)} default news sources.")
