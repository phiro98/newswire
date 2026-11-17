import re
import logging
from typing import Dict, List, Optional, Any, Tuple
import nltk

try:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    NLTK_VADER_AVAILABLE = True
except ImportError:
    NLTK_VADER_AVAILABLE = False

from app.config import settings

logger = logging.getLogger(__name__)

# Ensure VADER lexicon is present
def _ensure_vader():
    if NLTK_VADER_AVAILABLE:
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError:
            try:
                nltk.download("vader_lexicon", quiet=True)
            except Exception as e:
                logger.debug(f"Could not download vader_lexicon: {e}")

_ensure_vader()


# Default Authoritative Compliance Rule Dictionary
DEFAULT_COMPLIANCE_TAXONOMY = {
    "AML & Sanctions": {
        "severity": "CRITICAL",
        "keywords": [
            "money laundering", "anti-money laundering", "aml", "kyc",
            "sanctions", "sanctioned", "ofac", "sdn list", "terrorist financing",
            "shell company", "illicit funds", "politically exposed person", "pep",
            "embargo", "asset freeze", "smuggling"
        ]
    },
    "Bribery & Corruption": {
        "severity": "CRITICAL",
        "keywords": [
            "bribery", "bribe", "foreign corrupt practices", "fcpa",
            "kickback", "graft", "extortion", "embezzlement", "slush fund",
            "corrupt payment", "payoff"
        ]
    },
    "Fraud & Financial Crime": {
        "severity": "HIGH",
        "keywords": [
            "insider trading", "market manipulation", "securities fraud",
            "ponzi scheme", "wire fraud", "accounting fraud", "tax evasion",
            "forgery", "misappropriation", "falsified records", "pump and dump",
            "accounting irregularity"
        ]
    },
    "Cybersecurity & Data Privacy": {
        "severity": "HIGH",
        "keywords": [
            "data breach", "ransomware", "cyberattack", "gdpr violation",
            "ccpa penalty", "data leak", "zero-day exploit", "unauthorized access",
            "malware infection", "phishing campaign", "exfiltrated data"
        ]
    },
    "Regulatory & Legal Enforcement": {
        "severity": "MEDIUM",
        "keywords": [
            "sec investigation", "doj subpoena", "enforcement action",
            "regulatory penalty", "cease and desist", "consent decree",
            "antitrust probe", "monopoly lawsuit", "ftc action", "cftc order",
            "class action lawsuit", "whistleblower complaint"
        ]
    },
    "ESG & Human Rights": {
        "severity": "HIGH",
        "keywords": [
            "child labor", "forced labor", "human rights abuse",
            "toxic spill", "hazardous waste", "greenwashing", "environmental violation",
            "clean water act violation", "safety violation", "fatal accident"
        ]
    }
}


class SentimentEngine:
    """
    Performs sentiment classification (positive, neutral, negative)
    using VADER with a heuristic fallback lexicon.
    """

    def __init__(self):
        self.sia = None
        if NLTK_VADER_AVAILABLE:
            try:
                self.sia = SentimentIntensityAnalyzer()
            except Exception as e:
                logger.warning(f"Failed to initialize VADER analyzer: {e}")

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Calculates polarity compound score and maps to discrete sentiment category.
        """
        if not text or not text.strip():
            return {
                "label": "neutral",
                "score": 0.0,
                "breakdown": {"compound": 0.0, "pos": 0.0, "neu": 1.0, "neg": 0.0}
            }

        if self.sia:
            try:
                scores = self.sia.polarity_scores(text[:5000])  # Analyze first 5000 chars
                compound = scores.get("compound", 0.0)

                if compound >= 0.05:
                    label = "positive"
                elif compound <= -0.05:
                    label = "negative"
                else:
                    label = "neutral"

                return {
                    "label": label,
                    "score": round(compound, 3),
                    "breakdown": scores
                }
            except Exception as e:
                logger.error(f"Error in VADER sentiment scoring: {e}")

        # Rule-based fallback lexicon if VADER is unavailable
        return self._heuristic_sentiment(text)

    def _heuristic_sentiment(self, text: str) -> Dict[str, Any]:
        """Lightweight keyword-based sentiment fallback."""
        lower = text.lower()
        pos_words = {"growth", "profit", "success", "innovative", "gain", "surpassed", "record", "compliant", "approved"}
        neg_words = {"loss", "decline", "fall", "penalty", "violation", "breach", "lawsuit", "investigation", "crisis", "fraud"}

        pos_count = sum(1 for w in pos_words if re.search(r'\b' + w + r'\b', lower))
        neg_count = sum(1 for w in neg_words if re.search(r'\b' + w + r'\b', lower))

        diff = pos_count - neg_count
        if diff > 1:
            label, score = "positive", 0.4
        elif diff < -1:
            label, score = "negative", -0.4
        else:
            label, score = "neutral", 0.0

        return {
            "label": label,
            "score": score,
            "breakdown": {"compound": score, "pos": float(pos_count), "neu": 0.0, "neg": float(neg_count)}
        }


class ComplianceEngine:
    """
    Scans text against target compliance taxonomies and customizable keyword lists.
    Extracts contextual hit snippets and calculates an aggregate risk score (0-100).
    """

    def __init__(self, custom_taxonomy: Optional[Dict[str, Dict[str, Any]]] = None):
        self.taxonomy = custom_taxonomy or DEFAULT_COMPLIANCE_TAXONOMY
        self._compiled_patterns = self._compile_rules(self.taxonomy)

    def _compile_rules(self, taxonomy: Dict[str, Dict[str, Any]]) -> Dict[str, List[Tuple[str, re.Pattern, str]]]:
        """Pre-compiles regex patterns for high-throughput keyword scanning with word boundaries."""
        compiled = {}
        for category, data in taxonomy.items():
            severity = data.get("severity", "HIGH")
            keywords = data.get("keywords", [])
            rules = []
            for kw in keywords:
                # Word boundary match with escape for special chars
                pattern = re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
                rules.append((kw, pattern, severity))
            compiled[category] = rules
        return compiled

    def update_taxonomy(self, new_taxonomy: Dict[str, Dict[str, Any]]):
        """Allows dynamic live update of compliance rules."""
        self.taxonomy = new_taxonomy
        self._compiled_patterns = self._compile_rules(self.taxonomy)

    def extract_context_snippet(self, text: str, match_start: int, match_end: int, window: int = 60) -> str:
        """Extracts context snippet surrounding the target keyword match."""
        start = max(0, match_start - window)
        end = min(len(text), match_end + window)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return f"{prefix}{text[start:end].strip()}{suffix}"

    def inspect_compliance(self, text: str, title: str = "") -> Dict[str, Any]:
        """
        Scans title and text against compliance taxonomy.
        Returns:
            - is_flagged: bool
            - risk_score: float (0 - 100)
            - categories: List[str]
            - flags: List[Dict] with term, category, severity, and context snippet
        """
        full_text = f"{title}\n\n{text}"
        if not full_text.strip():
            return {
                "is_flagged": False,
                "risk_score": 0.0,
                "categories": [],
                "flags": []
            }

        flags: List[Dict[str, Any]] = []
        triggered_categories = set()
        total_risk_weight = 0.0

        severity_weights = {
            "CRITICAL": settings.COMPLIANCE_CRITICAL_WEIGHT,
            "HIGH": settings.COMPLIANCE_HIGH_WEIGHT,
            "MEDIUM": settings.COMPLIANCE_MEDIUM_WEIGHT,
            "LOW": settings.COMPLIANCE_LOW_WEIGHT,
        }

        for category, rules in self._compiled_patterns.items():
            for kw, pattern, severity in rules:
                matches = list(pattern.finditer(full_text))
                if matches:
                    triggered_categories.add(category)
                    weight = severity_weights.get(severity.upper(), 10.0)

                    # Diminishing returns for multiple hits of the same keyword
                    match_contribution = min(weight * len(matches), weight * 2.0)
                    total_risk_weight += match_contribution

                    # Record snippet for the first match of each keyword
                    first_match = matches[0]
                    snippet = self.extract_context_snippet(
                        full_text, first_match.start(), first_match.end()
                    )

                    flags.append({
                        "category": category,
                        "term": kw,
                        "severity": severity.upper(),
                        "context_snippet": snippet
                    })

        # Normalize risk score to 0 - 100 scale
        normalized_risk_score = round(min(100.0, total_risk_weight), 2)
        is_flagged = len(flags) > 0 and normalized_risk_score >= 10.0

        return {
            "is_flagged": is_flagged,
            "risk_score": normalized_risk_score,
            "categories": list(triggered_categories),
            "flags": flags
        }


VALID_CATEGORIES = [
    "Business & Finance",
    "Technology & AI",
    "Compliance & Sanctions",
    "World & Geopolitics",
    "Beauty",
    "Entertainment",
    "Sports"
]

CATEGORY_KEYWORDS = {
    "Beauty": [
        "skincare", "makeup", "cosmetics", "haircare", "fragrance", "perfume", 
        "lipstick", "serum", "moisturizer", "eyeshadow", "mascara", "dermatolog",
        "beauty routine", "manicure", "haircut", "sunscreen", "spf", "cleanser",
        "anti-aging", "aesthetician", "botox", "foundation", "concealer", "blush",
        "nail polish", "beauty brand", "hair styling", "wellness"
    ],
    "Entertainment": [
        "film", "movie", "tv", "television", "music", "celebrity", "actor", "actress",
        "hollywood", "album", "box office", "emmy", "oscar", "grammy", "concert",
        "cinema", "trailer", "streaming", "broadway", "pop star", "rapper", "director",
        "billboard", "netflix", "showrunner", "golden globe", "comic-con", "casting"
    ],
    "Sports": [
        "football", "soccer", "basketball", "nba", "nfl", "premier league", 
        "champions league", "tennis", "cricket", "golf", "olympics", "formula 1",
        "f1", "baseball", "mlb", "hockey", "nhl", "athlete", "tournament", "match",
        "score", "quarterback", "striker", "touchdown", "grand slam", "fifa", "championship"
    ],
    "Technology & AI": [
        "artificial intelligence", "ai", "machine learning", "llm", "gpt", "software",
        "hardware", "cyber", "semiconductor", "chip", "algorithm", "gadget", "smartphone",
        "apple", "google", "microsoft", "nvidia", "cloud", "crypto", "quantum computing",
        "robotics", "open ai", "deep learning", "silicon", "gpu", "app development"
    ],
    "World & Geopolitics": [
        "diplomacy", "treaty", "election", "parliament", "president", "prime minister",
        "united nations", "nato", "geopolitic", "foreign minister", "summit", "embassy",
        "border conflict", "ceasefire", "missile", "sovereignty", "white house", "kremlin",
        "middle east", "ukraine", "taiwan", "state department"
    ],
    "Business & Finance": [
        "market", "stock", "economy", "inflation", "gdp", "interest rate", "central bank",
        "federal reserve", "revenue", "earnings", "wall street", "banking", "merger",
        "acquisition", "shares", "nasdaq", "dow jones", "investor", "dividend", "venture capital",
        "private equity", "quarterly profit", "treasury", "bonds"
    ]
}


class CategoryClassifier:
    """
    Classifies articles into exactly one of the 7 core categories:
    Business & Finance, Technology & AI, Compliance & Sanctions,
    World & Geopolitics, Beauty, Entertainment, Sports.
    """

    def __init__(self):
        self._compiled = {
            cat: [re.compile(r'\b' + re.escape(kw) + r'\b', re.I) for kw in kws]
            for cat, kws in CATEGORY_KEYWORDS.items()
        }

    def classify(
        self, 
        title: str, 
        text: str, 
        source_category: Optional[str] = None, 
        is_compliance_flagged: bool = False,
        compliance_risk_score: float = 0.0
    ) -> str:
        # 1. High-risk compliance overrides generic categories
        if is_compliance_flagged and compliance_risk_score >= 25.0:
            return "Compliance & Sanctions"

        # Baseline source category mapping
        mapped_source_cat = None
        if source_category:
            s_lower = source_category.lower()
            if "beauty" in s_lower:
                mapped_source_cat = "Beauty"
            elif "entertain" in s_lower or "arts" in s_lower:
                mapped_source_cat = "Entertainment"
            elif "sport" in s_lower:
                mapped_source_cat = "Sports"
            elif "tech" in s_lower or "ai" in s_lower or "cyber" in s_lower:
                mapped_source_cat = "Technology & AI"
            elif "compliance" in s_lower or "enforce" in s_lower or "sanction" in s_lower or "regulat" in s_lower:
                mapped_source_cat = "Compliance & Sanctions"
            elif "world" in s_lower or "politic" in s_lower or "geopolitic" in s_lower:
                mapped_source_cat = "World & Geopolitics"
            elif "business" in s_lower or "financ" in s_lower or "market" in s_lower or "econom" in s_lower:
                mapped_source_cat = "Business & Finance"

        scores = {cat: 0 for cat in VALID_CATEGORIES}

        # Source category bonus
        if mapped_source_cat and mapped_source_cat in scores:
            scores[mapped_source_cat] += 4

        # Match keywords in title (weight 3) and body (weight 1)
        title_text = title.lower()
        body_text = text[:3000].lower() if text else ""

        for cat, patterns in self._compiled.items():
            for p in patterns:
                if p.search(title_text):
                    scores[cat] += 3
                elif p.search(body_text):
                    scores[cat] += 1

        # Check compliance keyword presence
        if is_compliance_flagged:
            scores["Compliance & Sanctions"] += 3

        # Resolve top category
        best_cat = max(scores.items(), key=lambda x: x[1])
        if best_cat[1] > 0:
            return best_cat[0]

        return mapped_source_cat or "Business & Finance"


class IntelligenceLayer:
    """
    Modular processing pipeline wrapper combining sentiment analysis,
    compliance scanning, and exact category classification.
    """

    def __init__(self):
        self.sentiment_engine = SentimentEngine()
        self.compliance_engine = ComplianceEngine()
        self.category_classifier = CategoryClassifier()

    def process_article(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies intelligence models to an extracted article dictionary.
        Returns the article data enriched with sentiment, compliance, and category tags.
        """
        title = article_data.get("title", "")
        summary = article_data.get("summary", "")
        body = article_data.get("text", "")
        source_category = article_data.get("source_category")

        # Composite text for analysis
        combined_text = f"{title}\n\n{summary}\n\n{body}"

        # 1. Sentiment Analysis
        sentiment = self.sentiment_engine.analyze_sentiment(combined_text)

        # 2. Compliance Flagging
        compliance = self.compliance_engine.inspect_compliance(text=body or summary, title=title)

        # 3. Exact Category Classification
        category = self.category_classifier.classify(
            title=title,
            text=body or summary,
            source_category=source_category,
            is_compliance_flagged=compliance["is_flagged"],
            compliance_risk_score=compliance["risk_score"]
        )

        # Merge results into article payload
        article_data["category"] = category
        article_data["sentiment_label"] = sentiment["label"]
        article_data["sentiment_score"] = sentiment["score"]
        article_data["sentiment_breakdown"] = sentiment["breakdown"]

        article_data["is_compliance_flagged"] = compliance["is_flagged"]
        article_data["compliance_risk_score"] = compliance["risk_score"]
        article_data["compliance_categories"] = compliance["categories"]
        article_data["compliance_flags"] = compliance["flags"]

        return article_data


# Global pipeline instance
analyzer_agent = IntelligenceLayer()
