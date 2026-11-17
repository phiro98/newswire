import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, 
    Float, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from app.database import Base


class NewsSource(Base):
    """Represents a subscribed news feed or API endpoint source."""
    __tablename__ = "news_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    source_type = Column(String(50), default="rss", nullable=False)  # 'rss', 'gnews', 'newsapi'
    category = Column(String(100), default="General", nullable=False)
    fetch_interval_minutes = Column(Integer, default=15, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_fetched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    articles = relationship("Article", back_populates="source", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "source_type": self.source_type,
            "category": self.category,
            "fetch_interval_minutes": self.fetch_interval_minutes,
            "is_active": self.is_active,
            "last_fetched_at": self.last_fetched_at.isoformat() if self.last_fetched_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "total_articles": len(self.articles) if self.articles else 0
        }


class Article(Base):
    """Core article entity with NLP extracted content, sentiment, and compliance risk flags."""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("news_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    
    title = Column(String(500), nullable=False, index=True)
    url = Column(Text, nullable=False)
    canonical_url = Column(Text, nullable=False, index=True)
    url_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA-256 for O(1) deduplication
    
    author = Column(String(255), nullable=True)
    publish_date = Column(DateTime, nullable=True, index=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    top_image = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)  # JSON-encoded array of keywords
    
    # Intelligence Layer Metrics
    sentiment_label = Column(String(20), default="neutral", index=True)  # 'positive', 'neutral', 'negative'
    sentiment_score = Column(Float, default=0.0)  # Compound score (-1.0 to 1.0)
    
    # Compliance Layer
    is_compliance_flagged = Column(Boolean, default=False, index=True)
    compliance_risk_score = Column(Float, default=0.0, index=True)  # 0 to 100
    compliance_categories = Column(Text, nullable=True)  # JSON array of triggered categories
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    source = relationship("NewsSource", back_populates="articles")
    compliance_flags = relationship(
        "ArticleComplianceFlag", 
        back_populates="article", 
        cascade="all, delete-orphan"
    )

    @property
    def keywords_list(self):
        if not self.keywords:
            return []
        try:
            return json.loads(self.keywords)
        except Exception:
            return []

    @property
    def compliance_categories_list(self):
        if not self.compliance_categories:
            return []
        try:
            return json.loads(self.compliance_categories)
        except Exception:
            return []


class ArticleComplianceFlag(Base):
    """Detailed hit record for specific compliance violation keywords and context snippets."""
    __tablename__ = "article_compliance_flags"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    term = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    context_snippet = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    article = relationship("Article", back_populates="compliance_flags")


class ComplianceRule(Base):
    """Customizable compliance classification rules and keyword dictionaries."""
    __tablename__ = "compliance_rules"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False, unique=True, index=True)
    keywords = Column(Text, nullable=False)  # JSON or comma-separated list of terms
    severity = Column(String(20), default="HIGH", nullable=False)  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class FetchLog(Base):
    """Audit log for tracking ingestion batches, status, and deduplication statistics."""
    __tablename__ = "fetch_logs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, nullable=True)
    source_name = Column(String(150), nullable=False)
    status = Column(String(30), nullable=False)  # 'SUCCESS', 'ERROR', 'PARTIAL'
    articles_discovered = Column(Integer, default=0)
    articles_ingested = Column(Integer, default=0)
    duplicates_skipped = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
