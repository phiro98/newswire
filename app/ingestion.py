import re
import hashlib
import logging
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, urljoin
from datetime import datetime
import requests
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from app.config import settings
from app.models import NewsSource, Article, FetchLog

logger = logging.getLogger(__name__)

# Tracking query parameters to strip for canonical deduplication
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "ref", "ref_src", "source", "cmpid",
    "ocid", "ncid", "mkt_tok", "mc_cid", "mc_eid", "_ga"
}


def normalize_url(raw_url: str, base_url: Optional[str] = None) -> str:
    """
    Standardizes a URL to ensure accurate deduplication:
    - Resolves relative URLs if base_url is provided.
    - Strips marketing/tracking query parameters (utm_*, fbclid, etc.).
    - Converts scheme and host to lowercase.
    - Removes URL fragments (#section).
    - Removes trailing slashes unless it's just the root domain.
    """
    if not raw_url:
        return ""

    if base_url:
        raw_url = urljoin(base_url, raw_url)

    parsed = urlparse(raw_url.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()

    # Strip default port numbers if present
    if netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Filter out tracking query params
    query_params = parse_qs(parsed.query, keep_blank_values=False)
    filtered_params = {
        k: v for k, v in query_params.items()
        if k.lower() not in TRACKING_PARAMS
    }
    # Sort query params for deterministic ordering
    sorted_query = urlencode(filtered_params, doseq=True)

    # Normalize path
    path = parsed.path
    if path.endswith("/") and len(path) > 1:
        path = path[:-1]

    # Build canonical URL (fragment is deliberately omitted)
    canonical = urlunparse((scheme, netloc, path, parsed.params, sorted_query, ""))
    return canonical


def generate_url_hash(canonical_url: str) -> str:
    """Generates a SHA-256 hash of the canonical URL for fast indexed O(1) deduplication."""
    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()


def is_article_duplicate(db: Session, canonical_url: str, url_hash: str) -> bool:
    """
    Checks if an article with the same URL hash or canonical URL already exists in the database.
    """
    exists = db.query(Article.id).filter(
        (Article.url_hash == url_hash) | (Article.canonical_url == canonical_url)
    ).first()
    return exists is not None


class IngestionModule:
    """
    Robust RSS and API parser supporting:
    - Standard RSS/Atom feeds (BBC, Reuters, SEC, etc.)
    - Google News (RSS & GNews API)
    - NewsAPI endpoints
    - Automated feed discovery from web page URLs
    """

    def __init__(self, request_timeout: int = settings.REQUEST_TIMEOUT_SECONDS):
        self.timeout = request_timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": settings.USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def parse_rss_feed(self, feed_url: str, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Fetches and parses an RSS or Atom feed using feedparser with HTTP session fallback.
        """
        articles: List[Dict[str, Any]] = []
        try:
            # Use requests first to reliably bypass restrictive user-agent blocks and handle SSL
            response = self.session.get(feed_url, timeout=self.timeout)
            response.raise_for_status()
            raw_content = response.content

            # Parse with feedparser
            feed = feedparser.parse(raw_content)

            if not feed.entries and feed.bozo:
                logger.warning(f"feedparser bozo exception on {feed_url}: {feed.bozo_exception}")

            for entry in feed.entries[:limit]:
                # Extract link
                link = getattr(entry, "link", None)
                if not link and "links" in entry:
                    for l in entry.links:
                        if l.get("rel") == "alternate":
                            link = l.get("href")
                            break
                    if not link and entry.links:
                        link = entry.links[0].get("href")

                if not link:
                    continue

                canonical = normalize_url(link)
                url_hash = generate_url_hash(canonical)

                # Extract publish date
                pub_date = None
                date_str = getattr(entry, "published", None) or getattr(entry, "updated", None)
                if date_str:
                    try:
                        pub_date = date_parser.parse(date_str)
                    except Exception:
                        pub_date = datetime.utcnow()
                else:
                    pub_date = datetime.utcnow()

                # Extract title and summary
                title = getattr(entry, "title", "Untitled Article")
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                author = getattr(entry, "author", None)

                # Clean HTML out of summary if needed
                if summary and "<" in summary:
                    summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)

                articles.append({
                    "title": title.strip(),
                    "url": link,
                    "canonical_url": canonical,
                    "url_hash": url_hash,
                    "publish_date": pub_date,
                    "author": author,
                    "snippet": summary[:500] if summary else "",
                    "source_type": "rss"
                })

        except Exception as e:
            logger.error(f"Error fetching RSS feed {feed_url}: {str(e)}", exc_info=True)

        return articles

    def parse_gnews(self, query: Optional[str] = None, topic: Optional[str] = None, 
                    api_key: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Parses Google News. If API key is provided, calls GNews REST API;
        otherwise, falls back to Google News RSS search (no API key required).
        """
        api_key = api_key or settings.GNEWS_API_KEY
        articles: List[Dict[str, Any]] = []

        if api_key:
            # GNews API v4
            endpoint = "https://gnews.io/api/v4/search" if query else "https://gnews.io/api/v4/top-headlines"
            params = {
                "token": api_key,
                "lang": "en",
                "max": min(limit, 100),
            }
            if query:
                params["q"] = query
            if topic:
                params["topic"] = topic

            try:
                res = self.session.get(endpoint, params=params, timeout=self.timeout)
                if res.status_code == 200:
                    data = res.json()
                    for item in data.get("articles", []):
                        canonical = normalize_url(item.get("url", ""))
                        articles.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "canonical_url": canonical,
                            "url_hash": generate_url_hash(canonical),
                            "publish_date": date_parser.parse(item.get("publishedAt")) if item.get("publishedAt") else datetime.utcnow(),
                            "author": item.get("source", {}).get("name"),
                            "snippet": item.get("description", ""),
                            "source_type": "gnews"
                        })
                    return articles
                else:
                    logger.warning(f"GNews API returned status {res.status_code}: {res.text}. Falling back to RSS.")
            except Exception as e:
                logger.error(f"Failed GNews API call: {e}. Falling back to RSS.")

        # Fallback to Google News RSS (always free and reliable)
        search_query = query or topic or "compliance OR sanctions OR regulatory"
        encoded_query = requests.utils.quote(search_query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        return self.parse_rss_feed(rss_url, limit=limit)

    def parse_newsapi(self, query: Optional[str] = None, category: Optional[str] = "general",
                      api_key: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Parses NewsAPI.org v2 endpoints if key is configured.
        """
        api_key = api_key or settings.NEWSAPI_KEY
        if not api_key:
            logger.warning("NewsAPI key not provided. Ingestion skipped.")
            return []

        articles: List[Dict[str, Any]] = []
        endpoint = "https://newsapi.org/v2/everything" if query else "https://newsapi.org/v2/top-headlines"
        params = {
            "apiKey": api_key,
            "language": "en",
            "pageSize": min(limit, 100)
        }
        if query:
            params["q"] = query
        elif category:
            params["category"] = category

        try:
            res = self.session.get(endpoint, params=params, timeout=self.timeout)
            if res.status_code == 200:
                data = res.json()
                for item in data.get("articles", []):
                    url = item.get("url", "")
                    if not url:
                        continue
                    canonical = normalize_url(url)
                    articles.append({
                        "title": item.get("title", ""),
                        "url": url,
                        "canonical_url": canonical,
                        "url_hash": generate_url_hash(canonical),
                        "publish_date": date_parser.parse(item.get("publishedAt")) if item.get("publishedAt") else datetime.utcnow(),
                        "author": item.get("author") or item.get("source", {}).get("name"),
                        "snippet": item.get("description", ""),
                        "source_type": "newsapi"
                    })
            else:
                logger.error(f"NewsAPI error {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"Exception during NewsAPI call: {e}")

        return articles

    def discover_feeds_from_url(self, website_url: str) -> List[str]:
        """
        Automatically inspects a website URL to discover published RSS or Atom feeds.
        """
        discovered: List[str] = []
        try:
            res = self.session.get(website_url, timeout=self.timeout)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            # Look for link tags with RSS/Atom MIME types
            feed_links = soup.find_all("link", type=re.compile(r"application\/(rss\+xml|atom\+xml)"))
            for link in feed_links:
                href = link.get("href")
                if href:
                    discovered.append(urljoin(website_url, href))

            # Test common standard feed endpoints if none found via link tags
            if not discovered:
                common_suffixes = ["/feed", "/rss", "/rss.xml", "/atom.xml", "/feed.xml"]
                for suffix in common_suffixes:
                    test_url = urljoin(website_url, suffix)
                    try:
                        head = self.session.head(test_url, timeout=5, allow_redirects=True)
                        content_type = head.headers.get("Content-Type", "").lower()
                        if head.status_code == 200 and any(t in content_type for t in ["xml", "rss", "atom"]):
                            discovered.append(test_url)
                            break
                    except Exception:
                        continue

        except Exception as e:
            logger.error(f"Failed to auto-discover feeds for {website_url}: {e}")

        return list(set(discovered))


# Global instance
ingestion_agent = IngestionModule()


def ingest_and_deduplicate(db: Session, source: NewsSource, limit: int = 25) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Fetches raw items from the given NewsSource and filters out duplicates against the database.
    Returns: (unprocessed_article_items, total_discovered, duplicates_skipped)
    """
    discovered_items: List[Dict[str, Any]] = []

    if source.source_type == "rss":
        discovered_items = ingestion_agent.parse_rss_feed(source.url, limit=limit)
    elif source.source_type == "gnews":
        discovered_items = ingestion_agent.parse_gnews(query=source.category or source.name, limit=limit)
    elif source.source_type == "newsapi":
        discovered_items = ingestion_agent.parse_newsapi(query=source.category or source.name, limit=limit)
    else:
        discovered_items = ingestion_agent.parse_rss_feed(source.url, limit=limit)

    total_discovered = len(discovered_items)
    unprocessed_items: List[Dict[str, Any]] = []
    duplicates_count = 0

    for item in discovered_items:
        if is_article_duplicate(db, item["canonical_url"], item["url_hash"]):
            duplicates_count += 1
            logger.debug(f"Skipping duplicate article: {item['canonical_url']}")
        else:
            unprocessed_items.append(item)

    # Update source last_fetched_at
    source.last_fetched_at = datetime.utcnow()
    db.commit()

    logger.info(
        f"Source '{source.name}': Discovered {total_discovered}, "
        f"Skipped {duplicates_count} duplicates, Ready for scraping: {len(unprocessed_items)}"
    )

    return unprocessed_items, total_discovered, duplicates_count
