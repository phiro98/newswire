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
    """Initializes database schema, performs safe migrations, and bootstraps default sources."""
    from app.models import NewsSource, Article
    from sqlalchemy import inspect, text

    Base.metadata.create_all(bind=engine)

    # Safe additive schema migration: Ensure 'category' column exists on 'articles'
    try:
        with engine.connect() as conn:
            inspector = inspect(engine)
            if "articles" in inspector.get_table_names():
                columns = [c["name"] for c in inspector.get_columns("articles")]
                if "category" not in columns:
                    logger.info("Migrating schema: Adding 'category' column to 'articles' table...")
                    try:
                        conn.execute(text("ALTER TABLE articles ADD COLUMN category VARCHAR(100) DEFAULT 'Business & Finance'"))
                        conn.commit()
                    except Exception as e:
                        logger.warning(f"Notice on column migration: {e}")
    except Exception as e:
        logger.warning(f"Schema inspection warning: {e}")

    # Seed or synchronize required default sources across all core categories
    with SessionLocal() as db:
        default_sources = [
            # Business & Finance
            {
                "name": "BBC Business News",
                "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
                "source_type": "rss",
                "category": "Business & Finance",
                "fetch_interval_minutes": 15,
                "is_active": True
            },
            # Technology & AI
            {
                "name": "BBC Technology",
                "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
                "source_type": "rss",
                "category": "Technology & AI",
                "fetch_interval_minutes": 15,
                "is_active": True
            },
            {
                "name": "Ars Technica",
                "url": "https://feeds.arstechnica.com/arstechnica/index",
                "source_type": "rss",
                "category": "Technology & AI",
                "fetch_interval_minutes": 20,
                "is_active": True
            },
            # World & Geopolitics
            {
                "name": "BBC World News",
                "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
                "source_type": "rss",
                "category": "World & Geopolitics",
                "fetch_interval_minutes": 15,
                "is_active": True
            },
            # Beauty
            {
                "name": "Allure Beauty",
                "url": "https://www.allure.com/feed/rss",
                "source_type": "rss",
                "category": "Beauty",
                "fetch_interval_minutes": 30,
                "is_active": True
            },
            {
                "name": "Byrdie Beauty",
                "url": "https://www.byrdie.com/rss",
                "source_type": "rss",
                "category": "Beauty",
                "fetch_interval_minutes": 30,
                "is_active": True
            },
            # Entertainment
            {
                "name": "Variety Entertainment",
                "url": "https://variety.com/feed/",
                "source_type": "rss",
                "category": "Entertainment",
                "fetch_interval_minutes": 20,
                "is_active": True
            },
            {
                "name": "BBC Entertainment & Arts",
                "url": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
                "source_type": "rss",
                "category": "Entertainment",
                "fetch_interval_minutes": 20,
                "is_active": True
            },
            # Sports
            {
                "name": "BBC Sport",
                "url": "https://feeds.bbci.co.uk/sport/rss.xml",
                "source_type": "rss",
                "category": "Sports",
                "fetch_interval_minutes": 15,
                "is_active": True
            },
            {
                "name": "ESPN Sports News",
                "url": "https://www.espn.com/espn/rss/news",
                "source_type": "rss",
                "category": "Sports",
                "fetch_interval_minutes": 15,
                "is_active": True
            },
            # Compliance & Sanctions
            {
                "name": "SEC Press Releases & Regulatory",
                "url": "https://www.sec.gov/news/pressreleases.rss",
                "source_type": "rss",
                "category": "Compliance & Sanctions",
                "fetch_interval_minutes": 30,
                "is_active": True
            },
            {
                "name": "Google News - Compliance & Sanctions",
                "url": "https://news.google.com/rss/search?q=sanctions+OR+anti-money+laundering+OR+bribery+investigation&hl=en-US&gl=US&ceid=US:en",
                "source_type": "rss",
                "category": "Compliance & Sanctions",
                "fetch_interval_minutes": 20,
                "is_active": True
            }
        ]

        added_count = 0
        for item in default_sources:
            existing = db.query(NewsSource).filter(NewsSource.url == item["url"]).first()
            if not existing:
                db.add(NewsSource(**item))
                added_count += 1
            else:
                # Update category to standard naming if legacy name was used
                if existing.category != item["category"]:
                    existing.category = item["category"]
                    existing.name = item["name"]

        db.commit()
        if added_count > 0:
            logger.info(f"Registered {added_count} new default news sources.")
