import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import nltk

try:
    from newspaper import Article as NewspaperArticle, Config as NewspaperConfig
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False

from app.config import settings

logger = logging.getLogger(__name__)

# Ensure essential NLTK data is ready for newspaper's NLP
def _ensure_nltk_resources():
    for resource in ["punkt", "punkt_tab", "stopwords"]:
        try:
            nltk.data.find(f"tokenizers/{resource}")
        except (LookupError, AttributeError):
            try:
                nltk.download(resource, quiet=True)
            except Exception as e:
                logger.debug(f"NLTK download notice for {resource}: {e}")

_ensure_nltk_resources()


class ScrapingAgent:
    """
    Robust scraping and parsing agent powered by newspaper4k, featuring:
    - Boilerplate, navigation, and advertisement removal
    - Clean body text extraction
    - Publish date and author resolution
    - Top image and media detection
    - Automated NLP extractive summarization and keyword generation
    - Resilient fallback engine for anti-scraping paywalls and custom markup
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": settings.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def _get_newspaper_config(self) -> Any:
        if not NEWSPAPER_AVAILABLE:
            return None
        config = NewspaperConfig()
        config.browser_user_agent = settings.USER_AGENT
        config.request_timeout = settings.REQUEST_TIMEOUT_SECONDS
        config.fetch_images = True
        config.memoize_articles = False
        config.language = settings.DEFAULT_LANGUAGE
        return config

    def scrape_article(
        self, 
        url: str, 
        fallback_title: Optional[str] = None,
        fallback_date: Optional[datetime] = None,
        fallback_author: Optional[str] = None,
        fallback_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Downloads target article URL, cleans away noise, and extracts core content and NLP artifacts.
        """
        logger.info(f"Scraping & parsing URL: {url}")
        result: Dict[str, Any] = {
            "url": url,
            "title": fallback_title or "Untitled Article",
            "text": fallback_summary or "",
            "summary": fallback_summary or "",
            "authors": [fallback_author] if fallback_author else [],
            "publish_date": fallback_date or datetime.utcnow(),
            "top_image": None,
            "keywords": [],
            "status": "PENDING",
            "error_message": None,
        }

        # Primary extraction using newspaper4k
        if NEWSPAPER_AVAILABLE:
            try:
                config = self._get_newspaper_config()
                article = NewspaperArticle(url=url, config=config)
                article.download()
                article.parse()

                # Extract cleaned content
                if article.text and len(article.text.strip()) > 80:
                    result["title"] = article.title.strip() if article.title else (fallback_title or "Untitled")
                    result["text"] = article.text.strip()
                    result["authors"] = article.authors or ([fallback_author] if fallback_author else [])
                    result["publish_date"] = article.publish_date or fallback_date or datetime.utcnow()
                    result["top_image"] = article.top_image if article.top_image else None

                    # NLP Processing (Extractive summary and keywords)
                    try:
                        article.nlp()
                        result["summary"] = article.summary.strip() if article.summary else ""
                        result["keywords"] = article.keywords if article.keywords else []
                    except Exception as nlp_err:
                        logger.warning(f"newspaper4k NLP parsing failed on {url}: {nlp_err}. Using fallback summarizer.")
                        result["summary"], result["keywords"] = self._fallback_nlp(result["text"])

                    result["status"] = "SUCCESS"
                    return result
                else:
                    logger.info(f"newspaper4k returned empty or short text on {url}. Engaging fallback parser.")

            except Exception as e:
                logger.warning(f"newspaper4k failed on {url}: {str(e)}. Attempting fallback parser.")

        # Resilient Fallback Parser using requests + BeautifulSoup
        return self._scrape_fallback(
            url=url,
            result=result,
            fallback_title=fallback_title,
            fallback_date=fallback_date,
            fallback_author=fallback_author,
            fallback_summary=fallback_summary
        )

    def _scrape_fallback(
        self, 
        url: str, 
        result: Dict[str, Any],
        fallback_title: Optional[str] = None,
        fallback_date: Optional[datetime] = None,
        fallback_author: Optional[str] = None,
        fallback_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Graceful fallback parser when newspaper4k is blocked by anti-bot headers or returns empty.
        """
        try:
            res = self.session.get(url, timeout=settings.REQUEST_TIMEOUT_SECONDS)
            res.raise_for_status()

            soup = BeautifulSoup(res.text, "html.parser")

            # Remove unwanted noise elements
            for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript", "svg", "form"]):
                tag.decompose()

            # Extract Title
            og_title = soup.find("meta", property="og:title")
            title_tag = soup.find("title")
            title = (og_title["content"] if og_title and og_title.get("content") 
                     else (title_tag.get_text(strip=True) if title_tag else fallback_title))
            result["title"] = title or "Untitled Article"

            # Extract Top Image
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                result["top_image"] = og_image["content"]

            # Extract Text from paragraphs within article or main container
            article_body = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"content|article|body", re.I))
            paragraphs = (article_body or soup).find_all("p")
            cleaned_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 25])

            if len(cleaned_text) < 50:
                cleaned_text = fallback_summary or soup.get_text(separator="\n", strip=True)

            result["text"] = cleaned_text or (fallback_summary or fallback_title or "")
            result["publish_date"] = fallback_date or datetime.utcnow()
            result["authors"] = [fallback_author] if fallback_author else []

            # Generate NLP summary and keywords from fallback text
            summary, keywords = self._fallback_nlp(result["text"])
            result["summary"] = summary or fallback_summary or result["text"][:300]
            result["keywords"] = keywords
            result["status"] = "FALLBACK_SUCCESS" if len(cleaned_text) > 100 else "PARTIAL"

        except Exception as e:
            logger.info(f"Fallback scraper engaged snippet mode for {url}: {str(e)}")
            result["status"] = "FALLBACK_SNIPPET"
            result["error_message"] = str(e)
            result["text"] = fallback_summary or (fallback_title or "")
            summary, keywords = self._fallback_nlp(result["text"])
            result["summary"] = summary or fallback_summary or result["text"][:300]
            result["keywords"] = keywords

        return result

    def _fallback_nlp(self, text: str) -> Tuple[str, List[str]]:
        """
        Extracts summary sentences and top keywords when native newspaper4k NLP is unavailable.
        """
        if not text:
            return "", []

        # Split sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

        # Use first 3 representative sentences as extractive summary
        summary = " ".join(sentences[:3])

        # Frequency-based keyword extraction
        words = re.findall(r'\b[A-Za-z]{4,}\b', text.lower())
        stop_words = {
            "this", "that", "with", "from", "have", "were", "which", "there",
            "their", "about", "would", "these", "other", "after", "first",
            "also", "could", "years", "state", "being", "under", "said"
        }
        filtered_words = [w for w in words if w not in stop_words]
        frequency = {}
        for w in filtered_words:
            frequency[w] = frequency.get(w, 0) + 1

        sorted_keywords = sorted(frequency.items(), key=lambda x: x[1], reverse=True)
        keywords = [kw for kw, _ in sorted_keywords[:10]]

        return summary, keywords


scraper_agent = ScrapingAgent()
