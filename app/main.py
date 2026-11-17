import os
import time
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.config import settings
from app.database import get_db, init_db, SessionLocal
from app.models import NewsSource, Article, ArticleComplianceFlag, FetchLog, ComplianceRule
from app.schemas import (
    SourceCreate, SourceUpdate, SourceResponse,
    ArticleSummaryResponse, ArticleDetailResponse,
    ComplianceRuleCreate, ComplianceRuleResponse,
    TriggerFetchRequest, TriggerFetchResponse,
    SystemStatusResponse, SystemMetricsResponse
)
from app.ingestion import ingestion_agent
from app.analyzer import analyzer_agent, DEFAULT_COMPLIANCE_TAXONOMY
from app.scheduler import (
    start_scheduler, stop_scheduler, get_scheduler_status,
    execute_pipeline_for_source, run_scheduled_polling_cycle
)

# Logging configuration
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("newswire.api")

START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for database initialization and background scheduler."""
    logger.info("Initializing Newswire Application Services...")
    init_db()

    # Load custom rules from database into analyzer if present
    db = SessionLocal()
    try:
        custom_rules = db.query(ComplianceRule).filter(ComplianceRule.is_active == True).all()
        if custom_rules:
            active_tax = dict(DEFAULT_COMPLIANCE_TAXONOMY)
            for r in custom_rules:
                try:
                    kw_list = json.loads(r.keywords) if r.keywords.startswith("[") else [k.strip() for k in r.keywords.split(",")]
                    active_tax[r.category] = {
                        "severity": r.severity,
                        "keywords": kw_list
                    }
                except Exception:
                    pass
            analyzer_agent.compliance_engine.update_taxonomy(active_tax)
    except Exception as e:
        logger.warning(f"Could not load custom rules on startup: {e}")
    finally:
        db.close()

    if settings.AUTO_POLL_ENABLED:
        start_scheduler()

    yield

    logger.info("Shutting down Newswire Application Services...")
    stop_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    description="Automated News Aggregator, Scraping Pipeline, and Compliance Monitoring API",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HEALTH & METRICS ENDPOINTS
# ============================================================================

@app.get("/health", tags=["System"])
def health_check():
    """Liveness probe for Docker container and orchestrator monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "app": settings.APP_NAME
    }


@app.get("/api/v1/status", response_model=SystemStatusResponse, tags=["System"])
def get_system_status(db: Session = Depends(get_db)):
    """Fetches real-time operational status and high-level platform KPIs."""
    uptime = time.time() - START_TIME
    active_sources = db.query(NewsSource).filter(NewsSource.is_active == True).count()
    total_articles = db.query(Article).count()
    flagged_articles = db.query(Article).filter(Article.is_compliance_flagged == True).count()

    # Sentiment distribution
    sentiment_counts = {
        "positive": db.query(Article).filter(Article.sentiment_label == "positive").count(),
        "neutral": db.query(Article).filter(Article.sentiment_label == "neutral").count(),
        "negative": db.query(Article).filter(Article.sentiment_label == "negative").count(),
    }

    sched_status = get_scheduler_status()

    return SystemStatusResponse(
        status="operational",
        uptime_seconds=round(uptime, 1),
        active_sources_count=active_sources,
        total_articles_count=total_articles,
        flagged_articles_count=flagged_articles,
        sentiment_ratio=sentiment_counts,
        scheduler_running=sched_status["running"],
        last_polling_time=sched_status["last_poll_time"]
    )


@app.get("/api/v1/metrics", response_model=SystemMetricsResponse, tags=["System"])
def get_system_metrics(db: Session = Depends(get_db)):
    """Provides detailed analytics on sentiment, compliance hits, and ingestion audits."""
    total_articles = db.query(Article).count()
    total_sources = db.query(NewsSource).count()
    active_sources = db.query(NewsSource).filter(NewsSource.is_active == True).count()
    flagged_articles = db.query(Article).filter(Article.is_compliance_flagged == True).count()

    sentiment_breakdown = {
        "positive": db.query(Article).filter(Article.sentiment_label == "positive").count(),
        "neutral": db.query(Article).filter(Article.sentiment_label == "neutral").count(),
        "negative": db.query(Article).filter(Article.sentiment_label == "negative").count(),
    }

    # Severity counts from ArticleComplianceFlag
    severity_breakdown = {
        "CRITICAL": db.query(ArticleComplianceFlag).filter(ArticleComplianceFlag.severity == "CRITICAL").count(),
        "HIGH": db.query(ArticleComplianceFlag).filter(ArticleComplianceFlag.severity == "HIGH").count(),
        "MEDIUM": db.query(ArticleComplianceFlag).filter(ArticleComplianceFlag.severity == "MEDIUM").count(),
        "LOW": db.query(ArticleComplianceFlag).filter(ArticleComplianceFlag.severity == "LOW").count(),
    }

    # Top triggered compliance categories
    top_categories = (
        db.query(
            ArticleComplianceFlag.category,
            func.count(ArticleComplianceFlag.id).label("hits")
        )
        .group_by(ArticleComplianceFlag.category)
        .order_by(desc("hits"))
        .limit(10)
        .all()
    )
    categories_data = [{"category": cat, "hits": hits} for cat, hits in top_categories]

    # Recent fetch logs
    recent_logs = (
        db.query(FetchLog)
        .order_by(desc(FetchLog.created_at))
        .limit(10)
        .all()
    )
    logs_data = [
        {
            "id": l.id,
            "source_name": l.source_name,
            "status": l.status,
            "discovered": l.articles_discovered,
            "ingested": l.articles_ingested,
            "skipped_duplicates": l.duplicates_skipped,
            "error": l.error_message,
            "timestamp": l.created_at.isoformat()
        }
        for l in recent_logs
    ]

    return SystemMetricsResponse(
        total_articles=total_articles,
        total_sources=total_sources,
        active_sources=active_sources,
        flagged_articles=flagged_articles,
        sentiment_breakdown=sentiment_breakdown,
        severity_breakdown=severity_breakdown,
        top_compliance_categories=categories_data,
        recent_fetch_logs=logs_data
    )


# ============================================================================
# SOURCE MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/v1/sources", response_model=List[SourceResponse], tags=["Sources"])
def list_sources(db: Session = Depends(get_db)):
    """Retrieves all registered news feeds and monitoring sources."""
    sources = db.query(NewsSource).order_by(NewsSource.id).all()
    result = []
    for s in sources:
        item = SourceResponse.model_validate(s)
        item.total_articles = db.query(Article).filter(Article.source_id == s.id).count()
        result.append(item)
    return result


@app.post("/api/v1/sources", response_model=SourceResponse, status_code=status.HTTP_201_CREATED, tags=["Sources"])
def create_source(source_in: SourceCreate, db: Session = Depends(get_db)):
    """
    Registers a new news source. Automatically detects RSS endpoints if a website root is supplied.
    """
    target_url = source_in.url.strip()

    # If it's an RSS source and doesn't look like an XML/RSS feed, attempt auto-discovery
    if source_in.source_type == "rss" and not any(ext in target_url.lower() for ext in [".rss", ".xml", "/feed", "/rss"]):
        discovered = ingestion_agent.discover_feeds_from_url(target_url)
        if discovered:
            logger.info(f"Auto-discovered RSS feed {discovered[0]} for {target_url}")
            target_url = discovered[0]

    # Check for existing source with identical URL
    existing = db.query(NewsSource).filter(NewsSource.url == target_url).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source with URL '{target_url}' already exists (ID: {existing.id})."
        )

    new_source = NewsSource(
        name=source_in.name,
        url=target_url,
        source_type=source_in.source_type,
        category=source_in.category,
        fetch_interval_minutes=source_in.fetch_interval_minutes,
        is_active=source_in.is_active,
        created_at=datetime.utcnow()
    )
    db.add(new_source)
    db.commit()
    db.refresh(new_source)

    resp = SourceResponse.model_validate(new_source)
    resp.total_articles = 0
    return resp


@app.get("/api/v1/sources/{source_id}", response_model=SourceResponse, tags=["Sources"])
def get_source(source_id: int, db: Session = Depends(get_db)):
    """Retrieves a single news source by ID."""
    source = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    resp = SourceResponse.model_validate(source)
    resp.total_articles = db.query(Article).filter(Article.source_id == source.id).count()
    return resp


@app.put("/api/v1/sources/{source_id}", response_model=SourceResponse, tags=["Sources"])
def update_source(source_id: int, source_update: SourceUpdate, db: Session = Depends(get_db)):
    """Updates configuration for an existing source."""
    source = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = source_update.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(source, field, val)

    db.commit()
    db.refresh(source)
    resp = SourceResponse.model_validate(source)
    resp.total_articles = db.query(Article).filter(Article.source_id == source.id).count()
    return resp


@app.delete("/api/v1/sources/{source_id}", tags=["Sources"])
def delete_source(source_id: int, db: Session = Depends(get_db)):
    """Removes a news source and its associated articles."""
    source = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
    return {"message": f"Source {source_id} ('{source.name}') and associated data deleted successfully."}


# ============================================================================
# FETCH & PIPELINE TRIGGER ENDPOINTS
# ============================================================================

def _run_fetch_batch(source_ids: List[int], limit_per_source: int):
    """Worker task executed in background or synchronously."""
    logger.info(f"Starting fetch execution for sources: {source_ids}")
    for sid in source_ids:
        execute_pipeline_for_source(sid, limit=limit_per_source)
    logger.info(f"Fetch execution finished for {len(source_ids)} sources.")


@app.post("/api/v1/fetch/trigger", response_model=TriggerFetchResponse, tags=["Pipeline Orchestration"])
def trigger_fetch(
    req: TriggerFetchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Triggers manual or batch re-fetch.
    If source_id is specified, fetches that source; otherwise triggers all active sources.
    Supports asynchronous execution via FastAPI BackgroundTasks.
    """
    if req.source_id:
        target_source = db.query(NewsSource).filter(NewsSource.id == req.source_id).first()
        if not target_source:
            raise HTTPException(status_code=404, detail=f"Source ID {req.source_id} not found.")
        source_ids = [target_source.id]
    else:
        active_sources = db.query(NewsSource).filter(NewsSource.is_active == True).all()
        source_ids = [s.id for s in active_sources]

    if not source_ids:
        return TriggerFetchResponse(
            message="No active news sources available to fetch.",
            sources_queued=0,
            status="completed"
        )

    if req.background:
        background_tasks.add_task(_run_fetch_batch, source_ids, req.limit_per_source)
        return TriggerFetchResponse(
            message=f"Queued background fetch for {len(source_ids)} source(s).",
            sources_queued=len(source_ids),
            status="queued"
        )
    else:
        # Synchronous execution
        _run_fetch_batch(source_ids, req.limit_per_source)
        return TriggerFetchResponse(
            message=f"Completed immediate fetch for {len(source_ids)} source(s).",
            sources_queued=len(source_ids),
            status="completed"
        )


# ============================================================================
# ARTICLE QUERY & FILTERING ENDPOINTS
# ============================================================================

@app.get("/api/v1/articles", response_model=List[ArticleSummaryResponse], tags=["Articles"])
def query_articles(
    sentiment: Optional[str] = Query(None, description="Filter by sentiment: positive, neutral, negative"),
    is_flagged: Optional[bool] = Query(None, description="Filter only compliance flagged articles"),
    topic: Optional[str] = Query(None, description="Filter by compliance topic/category or keyword"),
    source_id: Optional[int] = Query(None, description="Filter by source ID"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    search: Optional[str] = Query(None, description="Keyword search in title, summary, or content"),
    min_risk_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum compliance risk score"),
    limit: int = Query(25, ge=1, le=100, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """
    Queries processed articles with comprehensive multi-criteria filtering:
    - Sentiment ('positive', 'neutral', 'negative')
    - Compliance status (flagged vs clean)
    - Specific compliance categories (AML, Bribery, Fraud, Cyber, etc.)
    - Date ranges
    - Text search across title and extracted body
    """
    query = db.query(Article)

    if sentiment:
        query = query.filter(Article.sentiment_label == sentiment.lower())

    if is_flagged is not None:
        query = query.filter(Article.is_compliance_flagged == is_flagged)

    if min_risk_score is not None:
        query = query.filter(Article.compliance_risk_score >= min_risk_score)

    if source_id:
        query = query.filter(Article.source_id == source_id)

    if start_date:
        query = query.filter(Article.created_at >= start_date)

    if end_date:
        query = query.filter(Article.created_at <= end_date)

    if topic:
        topic_pattern = f"%{topic}%"
        query = query.filter(
            (Article.compliance_categories.ilike(topic_pattern)) |
            (Article.keywords.ilike(topic_pattern))
        )

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Article.title.ilike(search_pattern)) |
            (Article.summary.ilike(search_pattern)) |
            (Article.content.ilike(search_pattern))
        )

    articles = query.order_by(desc(Article.created_at)).offset(offset).limit(limit).all()

    results = []
    for a in articles:
        source_name = a.source.name if a.source else "Unknown Source"
        results.append(ArticleSummaryResponse(
            id=a.id,
            source_id=a.source_id,
            source_name=source_name,
            title=a.title,
            url=a.url,
            canonical_url=a.canonical_url,
            author=a.author,
            publish_date=a.publish_date,
            summary=a.summary,
            top_image=a.top_image,
            keywords=a.keywords_list,
            sentiment_label=a.sentiment_label,
            sentiment_score=a.sentiment_score,
            is_compliance_flagged=a.is_compliance_flagged,
            compliance_risk_score=a.compliance_risk_score,
            compliance_categories=a.compliance_categories_list,
            created_at=a.created_at
        ))

    return results


@app.get("/api/v1/articles/{article_id}", response_model=ArticleDetailResponse, tags=["Articles"])
def get_article_detail(article_id: int, db: Session = Depends(get_db)):
    """Retrieves full article details including clean body text and detailed compliance snippets."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    source_name = article.source.name if article.source else "Unknown Source"
    flags = [
        {
            "id": f.id,
            "category": f.category,
            "term": f.term,
            "severity": f.severity,
            "context_snippet": f.context_snippet,
            "created_at": f.created_at
        }
        for f in article.compliance_flags
    ]

    return ArticleDetailResponse(
        id=article.id,
        source_id=article.source_id,
        source_name=source_name,
        title=article.title,
        url=article.url,
        canonical_url=article.canonical_url,
        author=article.author,
        publish_date=article.publish_date,
        content=article.content,
        summary=article.summary,
        top_image=article.top_image,
        keywords=article.keywords_list,
        sentiment_label=article.sentiment_label,
        sentiment_score=article.sentiment_score,
        is_compliance_flagged=article.is_compliance_flagged,
        compliance_risk_score=article.compliance_risk_score,
        compliance_categories=article.compliance_categories_list,
        created_at=article.created_at,
        compliance_flags=flags
    )


@app.delete("/api/v1/articles/{article_id}", tags=["Articles"])
def delete_article(article_id: int, db: Session = Depends(get_db)):
    """Deletes an article record and its associated flags."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
    return {"message": f"Article {article_id} deleted successfully."}


# ============================================================================
# COMPLIANCE RULES ENDPOINTS
# ============================================================================

@app.get("/api/v1/compliance/rules", tags=["Compliance Configuration"])
def list_compliance_rules(db: Session = Depends(get_db)):
    """Returns currently active compliance categories, keywords, and severities."""
    custom_rules = db.query(ComplianceRule).all()
    custom_dict = {}
    for r in custom_rules:
        kws = json.loads(r.keywords) if r.keywords.startswith("[") else [k.strip() for k in r.keywords.split(",")]
        custom_dict[r.category] = {
            "id": r.id,
            "severity": r.severity,
            "keywords": kws,
            "is_active": r.is_active,
            "custom": True
        }

    # Combined with default built-in taxonomy
    merged = {}
    for cat, data in DEFAULT_COMPLIANCE_TAXONOMY.items():
        merged[cat] = {
            "severity": data["severity"],
            "keywords": data["keywords"],
            "is_active": True,
            "custom": False
        }
    merged.update(custom_dict)
    return {"compliance_rules": merged}


@app.post("/api/v1/compliance/rules", tags=["Compliance Configuration"])
def add_custom_compliance_rule(rule_in: ComplianceRuleCreate, db: Session = Depends(get_db)):
    """Adds or updates a custom compliance classification category and target keywords."""
    existing = db.query(ComplianceRule).filter(ComplianceRule.category == rule_in.category).first()
    if existing:
        existing.keywords = json.dumps(rule_in.keywords)
        existing.severity = rule_in.severity
        existing.is_active = rule_in.is_active
    else:
        new_rule = ComplianceRule(
            category=rule_in.category,
            keywords=json.dumps(rule_in.keywords),
            severity=rule_in.severity,
            is_active=rule_in.is_active,
            created_at=datetime.utcnow()
        )
        db.add(new_rule)

    db.commit()

    # Update in-memory analyzer engine
    all_rules = db.query(ComplianceRule).filter(ComplianceRule.is_active == True).all()
    active_tax = dict(DEFAULT_COMPLIANCE_TAXONOMY)
    for r in all_rules:
        kws = json.loads(r.keywords) if r.keywords.startswith("[") else [k.strip() for k in r.keywords.split(",")]
        active_tax[r.category] = {
            "severity": r.severity,
            "keywords": kws
        }
    analyzer_agent.compliance_engine.update_taxonomy(active_tax)

    return {"message": f"Compliance category '{rule_in.category}' configured successfully."}


# ============================================================================
# SCHEDULER & TASK MANAGEMENT
# ============================================================================

@app.get("/api/v1/tasks", tags=["Scheduler"])
def view_scheduled_tasks():
    """Returns background scheduler state and upcoming polling runs."""
    return get_scheduler_status()


@app.post("/api/v1/tasks/poll-now", tags=["Scheduler"])
def trigger_immediate_poll(background_tasks: BackgroundTasks):
    """Triggers an immediate background polling cycle across all active sources."""
    background_tasks.add_task(run_scheduled_polling_cycle)
    return {"message": "Immediate background polling cycle initiated."}


# ============================================================================
# INTERACTIVE CONTROL PANEL WEB INTERFACE
# ============================================================================

@app.get("/", response_class=HTMLResponse, tags=["Dashboard UI"])
def serve_dashboard():
    """Serves the rich real-time control panel & compliance monitoring dashboard."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.path.dirname(base_dir), "frontend", "index.html"),
        os.path.join(os.path.dirname(base_dir), "index.html"),
        os.path.join(base_dir, "index.html"),
        "frontend/index.html",
        "index.html"
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    return "<h1>Newswire API is running. Visit <a href='/docs'>/docs</a> for Swagger documentation.</h1>"


@app.get("/styles.css", include_in_schema=False)
def serve_styles():
    candidates = ["frontend/styles.css", "styles.css", "app/styles.css"]
    for path in candidates:
        if os.path.exists(path):
            return FileResponse(path, media_type="text/css")
    return HTMLResponse("", status_code=404)


@app.get("/app.js", include_in_schema=False)
def serve_js():
    candidates = ["frontend/app.js", "app.js", "app/app.js"]
    for path in candidates:
        if os.path.exists(path):
            return FileResponse(path, media_type="application/javascript")
    return HTMLResponse("", status_code=404)
