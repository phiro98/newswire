import json
import logging
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import NewsSource, Article, ArticleComplianceFlag, FetchLog
from app.ingestion import ingest_and_deduplicate
from app.scraper import scraper_agent
from app.analyzer import analyzer_agent

logger = logging.getLogger(__name__)

# Scheduler instance
scheduler = BackgroundScheduler()
_fetch_lock = threading.Lock()
_last_poll_time: Optional[datetime] = None


def execute_pipeline_for_source(source_id: int, limit: int = 25) -> Dict[str, Any]:
    """
    Executes the end-to-end pipeline for a single source:
    Ingestion -> Deduplication -> Scraping (newspaper4k) -> NLP Analysis (Sentiment + Compliance) -> DB Save.
    """
    db: Session = SessionLocal()
    stats = {
        "source_id": source_id,
        "discovered": 0,
        "duplicates": 0,
        "scraped": 0,
        "saved": 0,
        "flagged": 0,
        "status": "SUCCESS",
        "error": None
    }

    try:
        source = db.query(NewsSource).filter(NewsSource.id == source_id).first()
        if not source:
            stats["status"] = "ERROR"
            stats["error"] = f"Source {source_id} not found."
            return stats

        # 1. Ingestion & Deduplication
        candidates, discovered_count, duplicates_count = ingest_and_deduplicate(
            db=db, source=source, limit=limit
        )
        stats["discovered"] = discovered_count
        stats["duplicates"] = duplicates_count

        saved_articles = 0
        flagged_count = 0

        # Process each non-duplicate article through Scraper and Analyzer
        for item in candidates:
            try:
                # 2. Scraping with newspaper4k
                scraped = scraper_agent.scrape_article(
                    url=item["url"],
                    fallback_title=item.get("title"),
                    fallback_date=item.get("publish_date"),
                    fallback_author=item.get("author"),
                    fallback_summary=item.get("snippet")
                )
                stats["scraped"] += 1

                # Pass source classification context
                scraped["source_category"] = item.get("source_category") or source.category

                # 3. Intelligence Processing (Sentiment, Compliance, & Category)
                analyzed = analyzer_agent.process_article(scraped)

                # 4. Database Persistence
                article_record = Article(
                    source_id=source.id,
                    title=analyzed["title"],
                    url=item["url"],
                    canonical_url=item["canonical_url"],
                    url_hash=item["url_hash"],
                    category=analyzed.get("category", "Business & Finance"),
                    author=analyzed["authors"][0] if analyzed.get("authors") else None,
                    publish_date=analyzed.get("publish_date") or item.get("publish_date"),
                    content=analyzed["text"],
                    summary=analyzed.get("summary") or item.get("snippet") or "Extractive NLP summary pending.",
                    top_image=analyzed["top_image"],
                    keywords=json.dumps(analyzed.get("keywords", [])),
                    sentiment_label=analyzed["sentiment_label"],
                    sentiment_score=analyzed["sentiment_score"],
                    is_compliance_flagged=analyzed["is_compliance_flagged"],
                    compliance_risk_score=analyzed["compliance_risk_score"],
                    compliance_categories=json.dumps(analyzed.get("compliance_categories", [])),
                    created_at=datetime.utcnow()
                )
                db.add(article_record)
                db.flush()  # Generate article_record.id

                # Save associated compliance flags
                for flag_data in analyzed.get("compliance_flags", []):
                    flag_record = ArticleComplianceFlag(
                        article_id=article_record.id,
                        category=flag_data["category"],
                        term=flag_data["term"],
                        severity=flag_data["severity"],
                        context_snippet=flag_data.get("context_snippet"),
                        created_at=datetime.utcnow()
                    )
                    db.add(flag_record)

                if analyzed["is_compliance_flagged"]:
                    flagged_count += 1

                saved_articles += 1

            except Exception as item_err:
                logger.error(f"Failed processing article {item.get('url')}: {item_err}", exc_info=True)
                continue

        # Commit all successfully ingested articles
        db.commit()
        stats["saved"] = saved_articles
        stats["flagged"] = flagged_count

        # Log audit entry
        log_entry = FetchLog(
            source_id=source.id,
            source_name=source.name,
            status="SUCCESS",
            articles_discovered=discovered_count,
            articles_ingested=saved_articles,
            duplicates_skipped=duplicates_count,
            error_message=None,
            created_at=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()

    except Exception as e:
        db.rollback()
        stats["status"] = "ERROR"
        stats["error"] = str(e)
        logger.error(f"Error during ingestion for source {source_id}: {e}", exc_info=True)

        # Log failure audit
        try:
            source = db.query(NewsSource).filter(NewsSource.id == source_id).first()
            log_entry = FetchLog(
                source_id=source_id,
                source_name=source.name if source else "Unknown",
                status="ERROR",
                error_message=str(e),
                created_at=datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
        except Exception:
            pass

    finally:
        db.close()

    return stats


def run_scheduled_polling_cycle():
    """
    Executed by APScheduler on periodic intervals. Fetches and processes all active sources.
    """
    global _last_poll_time
    if not _fetch_lock.acquire(blocking=False):
        logger.info("Another ingestion cycle is currently active. Skipping scheduled cycle.")
        return

    try:
        logger.info("Starting scheduled automated news ingestion cycle...")
        _last_poll_time = datetime.utcnow()
        db: Session = SessionLocal()
        active_sources = db.query(NewsSource).filter(NewsSource.is_active == True).all()
        source_ids = [s.id for s in active_sources]
        db.close()

        total_saved = 0
        total_flagged = 0

        for sid in source_ids:
            res = execute_pipeline_for_source(sid, limit=settings.DEFAULT_ARTICLES_PER_FEED)
            total_saved += res.get("saved", 0)
            total_flagged += res.get("flagged", 0)

        logger.info(
            f"Automated polling cycle complete. Ingested {total_saved} articles "
            f"({total_flagged} compliance alerts flagged) across {len(source_ids)} sources."
        )
    finally:
        _fetch_lock.release()


def start_scheduler():
    """Starts the APScheduler background thread."""
    if not scheduler.running:
        interval = max(1, settings.POLLING_INTERVAL_MINUTES)
        scheduler.add_job(
            run_scheduled_polling_cycle,
            trigger=IntervalTrigger(minutes=interval),
            id="global_news_poller",
            name="Global News & Compliance Poller",
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"Background News Scheduler started with {interval}m polling interval.")


def stop_scheduler():
    """Stops the scheduler safely during application shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background News Scheduler shutdown completed.")


def get_scheduler_status() -> Dict[str, Any]:
    """Returns status and scheduled jobs."""
    jobs = []
    if scheduler.running:
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            })

    return {
        "running": scheduler.running,
        "last_poll_time": _last_poll_time.isoformat() if _last_poll_time else None,
        "interval_minutes": settings.POLLING_INTERVAL_MINUTES,
        "jobs": jobs
    }
