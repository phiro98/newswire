# Newswire: Automated News Aggregator & Compliance Monitoring Platform

A production-ready, enterprise-grade news aggregation and regulatory compliance monitoring system built with **Python 3.11**, **FastAPI**, **Newspaper4k**, **SQLAlchemy**, and a modular **AI Agent Intelligence Pipeline**.

---

## 🏛 System Architecture Overview

```
                      +---------------------------------------+
                      |       Subscribed News Sources         |
                      | (RSS/Atom Feeds, Google News, NewsAPI)|
                      +-------------------+-------------------+
                                          |
                                          v
      +=======================================================================+
      |  1. INGESTION & DEDUPLICATION AGENT (app/ingestion.py)                |
      |  - Canonical URL Normalization (strips UTM/tracking tokens)           |
      |  - SHA-256 Hash Generation & DB Lookup (O(1) Deduplication)          |
      |  - Automated RSS / Atom Feed Discovery                                |
      +===================================+===================================+
                                          | (Unprocessed Articles Only)
                                          v
      +=======================================================================+
      |  2. SCRAPING & EXTRACTION AGENT (app/scraper.py)                      |
      |  - Powered by Newspaper4k with Anti-Bot User-Agent Headers            |
      |  - Boilerplate, Navigation & Ad Removal                               |
      |  - Extractive NLP Summarization & Keyword Generation                  |
      |  - Resilient Fallback Parser (Requests + BeautifulSoup4)              |
      +===================================+===================================+
                                          | (Clean Body + Metadata + NLP)
                                          v
      +=======================================================================+
      |  3. INTELLIGENCE & PROCESSING LAYER (app/analyzer.py)                 |
      |  - VADER Polarity Scoring (Positive, Neutral, Negative)               |
      |  - Compliance Taxonomy Scanner (AML, Sanctions, Bribery, Fraud, etc.) |
      |  - Risk Score Calculation (0-100) & Context Snippet Extraction       |
      +===================================+===================================+
                                          |
                                          v
      +=======================================================================+
      |  4. PERSISTENCE & CONTROL PLANE (app/models.py & app/database.py)     |
      |  - PostgreSQL / SQLite with WAL Mode & Connection Pooling             |
      |  - Relational Schema: Sources, Articles, Compliance Flags, Audit Logs |
      +===================================+===================================+
                                          |
                     +--------------------+--------------------+
                     |                                         |
                     v                                         v
      +-------------------------------+     +----------------------------------+
      |  5. REST API & DASHBOARD      |     |  6. BACKGROUND SCHEDULER         |
      |  - FastAPI Async Endpoints    |     |  - APScheduler Polling Interval  |
      |  - Real-time Analytics & KPIs |     |  - Multi-threaded Batch Queue    |
      |  - Dark Mode Web Control UI   |     |  - Deduplication Audit Logging   |
      +-------------------------------+     +----------------------------------+
```

---

## 📦 Core Modules

### 1. Ingestion & Source Management Module (`app/ingestion.py`)
- **Canonical URL Normalization**: Resolves relative paths, lowercases domains, strips 15+ marketing and session tracking query parameters (`utm_*`, `fbclid`, `gclid`, `ref`, etc.), and removes URL fragments.
- **SHA-256 Deduplication**: Calculates deterministic 64-character SHA-256 hashes for canonical URLs, enabling $O(1)$ database deduplication to guarantee articles are never downloaded or processed more than once.
- **Multi-Protocol Feed Parsing**: Parses RSS, Atom, Google News (with fallback to free Google News RSS feeds that require no API key), and NewsAPI endpoints.
- **Automated Source Discovery**: Given any base website URL (e.g. `https://techcrunch.com`), automatically inspects the HTML for `<link rel="alternate" type="application/rss+xml">` or tests standard feed routes (`/feed`, `/rss.xml`).

### 2. Scraping & Parsing Agent (`app/scraper.py`)
- **Newspaper4k Integration**: Downloads full article content, strips clutter (banners, navigation bars, ads, cookie notices), and extracts clean text, authors, publish dates, top images, and media.
- **Automated NLP Summarization**: Generates concise extractive summaries and extracts high-frequency semantic keywords using NLTK and Newspaper4k NLP algorithms.
- **Resilient Fallback Engine**: If a website blocks Newspaper4k or serves dynamic markup, a secondary BeautifulSoup parser kicks in to extract OpenGraph metadata (`og:title`, `og:image`) and reconstruct clean paragraphs.

### 3. Intelligence & Processing Layer (`app/analyzer.py`)
- **Sentiment Analysis Engine**: Uses VADER (Valence Aware Dictionary and sEntiment Reasoner) to calculate polarity scores across compound (-1.0 to 1.0), positive, neutral, and negative metrics.
- **Compliance & Risk Flagging**: Real-time regulatory scanning against customizable compliance categories:
  * **AML & Sanctions** (Money laundering, OFAC, SDN, PEP, illicit funds, asset freeze)
  * **Bribery & Corruption** (FCPA, kickbacks, graft, embezzlement, extortion)
  * **Fraud & Financial Crime** (Insider trading, market manipulation, Ponzi schemes, wire fraud)
  * **Cybersecurity & Data Privacy** (Data breaches, ransomware, GDPR, CCPA, zero-days)
  * **Regulatory Enforcement** (SEC investigations, DOJ subpoenas, antitrust, consent decrees)
  * **ESG & Human Rights** (Child labor, forced labor, toxic spills, greenwashing)
- **Context Snippets & Risk Scoring**: Extracts 60-character surrounding text snippets highlighting triggered keywords and computes a normalized 0–100 risk score based on severity weights (CRITICAL: 35, HIGH: 20, MEDIUM: 10, LOW: 5).

### 4. FastAPI Control Panel & Endpoints (`app/main.py`)
- **Real-Time System Metrics**: High-level KPIs, uptime, source health, article counts, and sentiment ratios.
- **Multi-Criteria Article Search**: Filter articles by sentiment, compliance flagged status, topic/category, date range, or full-text query.
- **Pipeline Orchestration**: Trigger manual or automated batch re-fetches with synchronous or asynchronous (FastAPI BackgroundTasks) execution.
- **Interactive Control Panel Dashboard**: Built-in dark mode dashboard (`index.html`) served directly at `/` for live monitoring, source addition, and manual triggers.

### 5. Containerization & Deployment (`Dockerfile` & `docker-compose.yml`)
- **Multi-Stage Dockerfile**: Builds on `python:3.11-slim`, compiles dependencies in a builder stage, pre-downloads NLTK datasets (`punkt`, `punkt_tab`, `stopwords`, `vader_lexicon`), and runs under an unprivileged `appuser` for maximum security.
- **Docker Compose Orchestration**: Seamlessly coordinates the FastAPI application service and a PostgreSQL 15 container with persistent volume storage, healthchecks, and automatic reconnection.

---

## 🚀 Quickstart with Docker Compose

### Prerequisites
- Docker Engine (v20.10+)
- Docker Compose (v2.0+)

### 1. Clone & Configure
```bash
git clone <repo_url>
cd newswire

# Copy environment variables template
cp .env.example .env
```

### 2. Build and Start Services
```bash
docker compose up --build -d
```

### 3. Verify Container Health
```bash
docker compose ps
```
Both `newswire_postgres` and `newswire_api` will show `(healthy)`.

### 4. Open the Application
- **Production Web Dashboard (Nginx Frontend)**: [http://localhost:3000/](http://localhost:3000/)
- **FastAPI Control Plane (Direct API & Dashboard)**: [http://localhost:8000/](http://localhost:8000/)
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc API Reference**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health) or [http://localhost:3000/health](http://localhost:3000/health)

### 5. Managing the Deployment
```bash
# View live application and ingestion logs
docker compose logs -f api

# Stop all containers
docker compose down

# Stop and wipe database volume (clean reset)
docker compose down -v
```

---

## 💻 Running Locally (Without Docker)

You can run the application directly on your machine with Python and SQLite:

### 1. Create and Activate Virtual Environment
```bash
# On Linux / macOS
python3 -m venv venv
source venv/bin/activate

# On Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Download Required NLTK Corpora
```bash
python -m nltk.downloader punkt punkt_tab stopwords vader_lexicon
```

### 4. Start the Application
```bash
python run.py
```
Or via Uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The app will initialize SQLite database `data/news.db` with WAL mode automatically and bootstrap 5 authoritative news sources.

---

## 📡 RESTful API Reference

### System & Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Container liveness check |
| `GET` | `/api/v1/status` | System health, uptime, total articles, sentiment ratio |
| `GET` | `/api/v1/metrics` | In-depth analytics, top compliance categories, audit logs |

**Example: Get System Status**
```bash
curl -X GET http://localhost:8000/api/v1/status
```

---

### Sources Management

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/sources` | List all configured news feeds |
| `POST` | `/api/v1/sources` | Register a new RSS or API source (supports auto-discovery) |
| `GET` | `/api/v1/sources/{id}` | Get source details and article count |
| `PUT` | `/api/v1/sources/{id}` | Update source configuration |
| `DELETE` | `/api/v1/sources/{id}` | Delete source and related articles |

**Example: Add a New Source**
```bash
curl -X POST http://localhost:8000/api/v1/sources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Financial Times Regulatory News",
    "url": "https://www.ft.com/companies/financial-services",
    "source_type": "rss",
    "category": "Regulatory & Finance",
    "fetch_interval_minutes": 15,
    "is_active": true
  }'
```

---

### Ingestion & Pipeline Orchestration

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/fetch/trigger` | Trigger immediate ingestion for a specific source or all sources |
| `POST` | `/api/v1/tasks/poll-now` | Run scheduled polling cycle immediately in background |
| `GET` | `/api/v1/tasks` | View active scheduler jobs and next run timestamps |

**Example: Trigger Ingestion for All Sources (Asynchronous)**
```bash
curl -X POST http://localhost:8000/api/v1/fetch/trigger \
  -H "Content-Type: application/json" \
  -d '{"background": true, "limit_per_source": 20}'
```

---

### Query Processed Articles & Compliance Intelligence

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/articles` | Filter articles by sentiment, compliance flag, topic, date |
| `GET` | `/api/v1/articles/{id}` | Retrieve full article text, NLP summary, and context snippets |
| `DELETE` | `/api/v1/articles/{id}` | Delete a single article |

**Supported Query Parameters for `/api/v1/articles`**:
- `sentiment`: `positive` | `neutral` | `negative`
- `is_flagged`: `true` | `false`
- `topic`: Keyword search within compliance categories or NLP keywords
- `search`: Full-text search across article title, summary, and extracted body
- `min_risk_score`: Filter articles with risk score $\ge$ threshold (e.g. `20.0`)
- `start_date` / `end_date`: ISO 8601 timestamps
- `limit` (default: 25) & `offset` (pagination)

**Example: Search for Negative Articles Flagged for Sanctions or AML**
```bash
curl -X GET "http://localhost:8000/api/v1/articles?sentiment=negative&is_flagged=true&topic=Sanctions&limit=10"
```

---

### Customizing Compliance Rules

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/compliance/rules` | List all active compliance taxonomies and keywords |
| `POST` | `/api/v1/compliance/rules` | Add or update custom compliance categories and keywords |

**Example: Add Custom Compliance Rule**
```bash
curl -X POST http://localhost:8000/api/v1/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "category": "Antitrust & Cartels",
    "keywords": ["price fixing", "cartel", "bid rigging", "market allocation", "collusion"],
    "severity": "CRITICAL",
    "is_active": true
  }'
```

---

## ⚙️ Configuration Reference (`.env`)

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `Newswire Compliance Monitor` | Display title of application |
| `DATABASE_URL` | `sqlite:///./data/news.db` | Database connection string (PostgreSQL or SQLite) |
| `AUTO_POLL_ENABLED` | `True` | Whether background scheduler runs automatically |
| `POLLING_INTERVAL_MINUTES` | `15` | Default automated polling interval |
| `DEFAULT_ARTICLES_PER_FEED` | `25` | Maximum articles to extract per feed per cycle |
| `REQUEST_TIMEOUT_SECONDS` | `15` | Network timeout for feed and page fetching |
| `NEWSAPI_KEY` | `None` | (Optional) API key for NewsAPI.org |
| `GNEWS_API_KEY` | `None` | (Optional) API key for GNews.io |
| `COMPLIANCE_CRITICAL_WEIGHT` | `35.0` | Risk score addition per CRITICAL hit |
| `COMPLIANCE_HIGH_WEIGHT` | `20.0` | Risk score addition per HIGH hit |
| `COMPLIANCE_MEDIUM_WEIGHT` | `10.0` | Risk score addition per MEDIUM hit |
| `COMPLIANCE_LOW_WEIGHT` | `5.0` | Risk score addition per LOW hit |

---

## 🔒 Enterprise & Security Highlights

1. **Non-Root Container**: Runs under `appuser` (UID 1001) in Docker, complying with enterprise container security requirements.
2. **Offline-Ready NLTK Models**: NLTK tokenizers and lexicons are pre-baked into the image during the Docker build stage, eliminating external runtime model download failures.
3. **Resilient Network Handling**: Robust retry and fallback logic protects against 403 Forbidden responses, SSL certificate anomalies, and malformed RSS feeds.
4. **Deterministic O(1) Deduplication**: Canonical URLs are stripped of tracking cookies and hashed with SHA-256 to ensure duplicate articles are skipped before any scraping overhead occurs.

---

## 📄 License
This project is licensed under the MIT License.
