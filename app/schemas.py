from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class SourceBase(BaseModel):
    name: str = Field(..., example="Reuters Business News")
    url: str = Field(..., example="https://feeds.bbci.co.uk/news/business/rss.xml")
    source_type: str = Field(default="rss", example="rss")
    category: str = Field(default="General", example="Business & Finance")
    fetch_interval_minutes: int = Field(default=15, ge=1, le=1440, example=15)
    is_active: bool = Field(default=True, example=True)


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    source_type: Optional[str] = None
    category: Optional[str] = None
    fetch_interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    is_active: Optional[bool] = None


class SourceResponse(SourceBase):
    id: int
    last_fetched_at: Optional[datetime] = None
    created_at: datetime
    total_articles: int = 0

    class Config:
        from_attributes = True


class ComplianceFlagResponse(BaseModel):
    id: int
    category: str
    term: str
    severity: str
    context_snippet: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ArticleSummaryResponse(BaseModel):
    id: int
    source_id: Optional[int] = None
    source_name: Optional[str] = None
    title: str
    url: str
    canonical_url: str
    author: Optional[str] = None
    publish_date: Optional[datetime] = None
    summary: Optional[str] = None
    top_image: Optional[str] = None
    keywords: List[str] = []
    sentiment_label: str
    sentiment_score: float
    is_compliance_flagged: bool
    compliance_risk_score: float
    compliance_categories: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ArticleDetailResponse(ArticleSummaryResponse):
    content: str
    compliance_flags: List[ComplianceFlagResponse] = []


class ComplianceRuleCreate(BaseModel):
    category: str = Field(..., example="Sanctions & AML")
    keywords: List[str] = Field(..., example=["money laundering", "sanctions", "ofac", "illicit funds"])
    severity: str = Field(default="HIGH", example="HIGH")
    is_active: bool = Field(default=True, example=True)


class ComplianceRuleResponse(BaseModel):
    id: int
    category: str
    keywords: List[str]
    severity: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TriggerFetchRequest(BaseModel):
    source_id: Optional[int] = Field(None, description="Optional ID of specific source to fetch. If null, all active sources are fetched.")
    limit_per_source: Optional[int] = Field(15, ge=1, le=100, description="Max articles to discover per source")
    background: bool = Field(True, description="Whether to execute ingestion in a background task")


class TriggerFetchResponse(BaseModel):
    message: str
    task_id: Optional[str] = None
    sources_queued: int = 0
    status: str = "initiated"


class SystemStatusResponse(BaseModel):
    status: str
    uptime_seconds: float
    active_sources_count: int
    total_articles_count: int
    flagged_articles_count: int
    sentiment_ratio: Dict[str, int]
    scheduler_running: bool
    last_polling_time: Optional[datetime] = None


class SystemMetricsResponse(BaseModel):
    total_articles: int
    total_sources: int
    active_sources: int
    flagged_articles: int
    sentiment_breakdown: Dict[str, int]
    severity_breakdown: Dict[str, int]
    top_compliance_categories: List[Dict[str, Any]]
    recent_fetch_logs: List[Dict[str, Any]]
