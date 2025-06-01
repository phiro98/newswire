import os
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Query
import httpx
import csv
from io import StringIO

# --- Configuration: Replace with your actual API Keys ---
# In a real application, store these securely, e.g., in environment variables
# For now, put them directly or load from a .env file (if using python-dotenv)
# from dotenv import load_dotenv
# load_dotenv() # Load environment variables from .env file

NEWSAPI_ORG_API_KEY = "YOUR_NEWSAPI_ORG_API_KEY"  # e.g., os.getenv("NEWSAPI_ORG_API_KEY")
GNEWS_API_KEY = "YOUR_GNEWS_API_KEY"            # e.g., os.getenv("GNEWS_API_KEY")
NEWSDATA_IO_API_KEY = "YOUR_NEWSDATA_IO_API_KEY"    # e.g., os.getenv("NEWSDATA_IO_API_KEY")
MEDIASTACK_API_KEY = "YOUR_MEDIASTACK_API_KEY"      # e.g., os.getenv("MEDIASTACK_API_KEY")
CURRENTS_API_KEY = "YOUR_CURRENTS_API_KEY"          # e.g., os.getenv("CURRENTS_API_KEY")

# --- FastAPI App Initialization ---
app = FastAPI(
    title="News Aggregator API",
    description="API to fetch news from various news providers.",
    version="1.0.0"
)

# --- HTTP Client Initialization ---
# Use a global httpx client for connection pooling and efficiency
# It's recommended to manage client lifecycle in a real app, e.g., via lifespan events
# For simplicity, we'll initialize it here.
http_client = httpx.AsyncClient(timeout=30.0) # Increased timeout for potentially slower APIs

# --- Lifespan Events (Optional but Recommended for httpx client) ---
# This ensures the httpx client is properly closed when the app shuts down
@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

# --- Helper Function for API Requests ---
async def fetch_from_api(url: str, params: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    try:
        response = await http_client.get(url, params=params, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error from external API: {e.response.text}"
        )
    except httpx.RequestError as e:
        print(f"Request error occurred: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Network error or request timeout: {e}"
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {e}"
        )

# --- NewsAPI.org Endpoint ---
@app.get("/newsapi-org/top-headlines", summary="Fetch top headlines from NewsAPI.org")
async def get_newsapi_org_headlines(
    query: Optional[str] = Query(None, description="Keywords or phrases for the search."),
    country: Optional[str] = Query("in", description="The 2-letter ISO 3166-1 code of the country you want to get headlines for."),
    category: Optional[str] = Query(None, description="The category you want to get headlines for. Options: business, entertainment, general, health, science, sports, technology."),
    sources: Optional[str] = Query(None, description="A comma-seperated string of identifiers for the news sources or blogs you want to get headlines from."),
    page_size: int = Query(20, ge=1, le=100, description="The number of results to return per page (1-100)."),
    page: int = Query(1, ge=1, description="The number of the page to return.")
) -> Dict[str, Any]:
    """
    Fetches top headlines from NewsAPI.org.
    """
    if not NEWSAPI_ORG_API_KEY or NEWSAPI_ORG_API_KEY == "YOUR_NEWSAPI_ORG_API_KEY":
        raise HTTPException(status_code=500, detail="NewsAPI.org API key is not configured.")

    base_url = "https://newsapi.org/v2/top-headlines"
    params = {
        "apiKey": NEWSAPI_ORG_API_KEY,
        "q": query,
        "country": country,
        "category": category,
        "sources": sources,
        "pageSize": page_size,
        "page": page
    }
    # Remove None values from params
    params = {k: v for k, v in params.items() if v is not None}
    return await fetch_from_api(base_url, params)

# --- GNews Endpoint ---
@app.get("/gnews/search", summary="Search for articles on GNews")
async def get_gnews_articles(
    query: str = Query(..., description="Keywords or phrases for the search."),
    lang: Optional[str] = Query("en", description="The language of the articles to search for (e.g., 'en', 'es', 'fr')."),
    country: Optional[str] = Query("us", description="The 2-letter ISO 3166-1 code of the country to search in."),
    max_articles: int = Query(10, ge=1, le=100, description="The maximum number of articles to return (1-100)."),
    in_title: Optional[str] = Query(None, description="Search for articles where the query is found in the title."),
    in_description: Optional[str] = Query(None, description="Search for articles where the query is found in the description.")
) -> Dict[str, Any]:
    """
    Searches for articles using the GNews API.
    """
    if not GNEWS_API_KEY or GNEWS_API_KEY == "YOUR_GNEWS_API_KEY":
        raise HTTPException(status_code=500, detail="GNews API key is not configured.")

    base_url = "https://gnews.io/api/v4/search"
    params = {
        "token": GNEWS_API_KEY,
        "q": query,
        "lang": lang,
        "country": country,
        "max": max_articles,
        "in": f"{'title,' if in_title else ''}{'description' if in_description else ''}".strip(',') if in_title or in_description else None
    }
    # Remove None values from params
    params = {k: v for k, v in params.items() if v is not None}
    return await fetch_from_api(base_url, params)

# --- NewsData.io Endpoint ---
@app.get("/newsdata-io/latest", summary="Fetch latest news from NewsData.io")
async def get_newsdata_io_latest(
    query: Optional[str] = Query(None, description="Keywords to search in article content."),
    language: Optional[str] = Query("en", description="Language of news articles (e.g., 'en', 'es', 'fr')."),
    country: Optional[str] = Query("us", description="Country of news articles (e.g., 'us', 'gb', 'in')."),
    category: Optional[str] = Query(None, description="Category of news articles (e.g., 'business', 'sports', 'health')."),
    domain_url: Optional[str] = Query(None, description="Search news from specific domain (e.g., 'nytimes.com')."),
    size: int = Query(10, ge=1, le=50, description="Number of results to return (1-50).")
) -> Dict[str, Any]:
    """
    Fetches the latest news articles from NewsData.io.
    """
    if not NEWSDATA_IO_API_KEY or NEWSDATA_IO_API_KEY == "YOUR_NEWSDATA_IO_API_KEY":
        raise HTTPException(status_code=500, detail="NewsData.io API key is not configured.")

    base_url = "https://newsdata.io/api/1/latest"
    params = {
        "apikey": NEWSDATA_IO_API_KEY,
        "q": query,
        "language": language,
        "country": country,
        "category": category,
        "domainurl": domain_url,
        "size": size
    }
    # Remove None values from params
    params = {k: v for k, v in params.items() if v is not None}
    return await fetch_from_api(base_url, params)

# --- Mediastack Endpoint ---
@app.get("/mediastack/news", summary="Fetch news from Mediastack")
async def get_mediastack_news(
    query: Optional[str] = Query(None, description="Keywords to search for in news articles."),
    countries: Optional[str] = Query("us", description="Comma-separated list of 2-letter ISO 3166-1 country codes."),
    languages: Optional[str] = Query("en", description="Comma-separated list of 2-letter ISO 639-1 language codes."),
    categories: Optional[str] = Query(None, description="Comma-separated list of categories (e.g., 'business', 'sports')."),
    sources: Optional[str] = Query(None, description="Comma-separated list of news sources."),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results to return (1-100)."),
    offset: int = Query(0, ge=0, description="Offset for pagination.")
) -> Dict[str, Any]:
    """
    Fetches news articles using the Mediastack API.
    """
    if not MEDIASTACK_API_KEY or MEDIASTACK_API_KEY == "YOUR_MEDIASTACK_API_KEY":
        raise HTTPException(status_code=500, detail="Mediastack API key is not configured.")

    base_url = "http://api.mediastack.com/v1/news"
    params = {
        "access_key": MEDIASTACK_API_KEY,
        "keywords": query,
        "countries": countries,
        "languages": languages,
        "categories": categories,
        "sources": sources,
        "limit": limit,
        "offset": offset
    }
    # Remove None values from params
    params = {k: v for k, v in params.items() if v is not None}
    return await fetch_from_api(base_url, params)

# --- Currents API Endpoint ---
@app.get("/currents-api/search", summary="Search for news on Currents API")
async def get_currents_api_search(
    query: str = Query(..., description="Keywords to search for in articles."),
    language: Optional[str] = Query("en", description="Language of articles (e.g., 'en', 'es')."),
    country: Optional[str] = Query(None, description="Country of articles (e.g., 'US', 'GB')."),
    category: Optional[str] = Query(None, description="Category of articles (e.g., 'general', 'technology')."),
    start_date: Optional[str] = Query(None, description="Start date for articles (YYYY-MM-DDTHH:MM:SS format)."),
    end_date: Optional[str] = Query(None, description="End date for articles (YYYY-MM-DDTHH:MM:SS format)."),
    page_number: int = Query(1, ge=1, description="Page number for pagination."),
    page_size: int = Query(10, ge=1, le=200, description="Number of results per page (1-200).")
) -> Dict[str, Any]:
    """
    Searches for news articles using the Currents API.
    """
    if not CURRENTS_API_KEY or CURRENTS_API_KEY == "YOUR_CURRENTS_API_KEY":
        raise HTTPException(status_code=500, detail="Currents API key is not configured.")

    base_url = "https://api.currentsapi.services/v1/search"
    params = {
        "apiKey": CURRENTS_API_KEY,
        "keywords": query,
        "language": language,
        "country": country,
        "category": category,
        "start_date": start_date,
        "end_date": end_date,
        "page_number": page_number,
        "page_size": page_size
    }
    # Remove None values from params
    params = {k: v for k, v in params.items() if v is not None}
    return await fetch_from_api(base_url, params)


# --- GDELT 2.0 Global Knowledge Graph Endpoint ---
# GDELT is different: it provides CSV data, not direct JSON for content.
# We'll fetch the latest daily/hourly CSV and extract URLs.
# Note: GDELT URLs change, so you might need a more robust way to find the latest
# GDELT URL (e.g., by checking their master file lists).
# For simplicity, we'll target a recent daily master file for this example.
# A better approach would be to parse http://data.gdeltproject.org/gdeltv2/masterfilelist.txt
# to get the latest daily or hourly file.

@app.get("/gdelt/latest-urls", summary="Fetch latest news URLs from GDELT 2.0 Global Knowledge Graph")
async def get_gdelt_latest_urls(
    limit: int = Query(50, ge=1, description="Maximum number of URLs to return from the GDELT data.")
) -> List[Dict[str, str]]:
    """
    Fetches the latest GDELT 2.0 Global Knowledge Graph (GKG) CSV data
    and extracts news article URLs.
    """
    # GDELT's daily GKG data file. This URL points to the latest daily file list.
    # A more robust solution would dynamically find the latest hourly/daily file URL.
    # For now, we'll use a representative URL format.
    # To get the latest GKG file:
    # 1. Fetch http://data.gdeltproject.org/gdeltv2/masterfilelist.txt
    # 2. Parse it to find the latest 'gkg.csv' entry.
    # Example for latest daily GKG URL (updates daily):
    # This URL pattern changes daily/hourly. You'll need to fetch the
    # masterfilelist.txt and parse it to get the correct URL for the latest file.
    # For a quick demo, I'll use a placeholder or a direct link to the daily master list.

    try:
        # Step 1: Get the latest GKG master file list URL
        master_list_url = "http://data.gdeltproject.org/gdeltv2/masterfilelist.txt"
        master_list_response = await http_client.get(master_list_url)
        master_list_response.raise_for_status()
        master_list_content = master_list_response.text

        # Step 2: Find the latest GKG daily file
        latest_gkg_url = None
        for line in master_list_content.splitlines():
            parts = line.split(" ")
            if len(parts) == 3 and parts[2].endswith(".gkg.csv.zip"):
                latest_gkg_url = parts[2].replace(".zip", "") # Get the .csv URL
                break

        if not latest_gkg_url:
            raise HTTPException(status_code=500, detail="Could not find latest GDELT GKG CSV URL.")

        # Step 3: Fetch the GDELT GKG CSV data
        print(f"Fetching GDELT data from: {latest_gkg_url}")
        gdelt_response = await http_client.get(latest_gkg_url)
        gdelt_response.raise_for_status()

        # Step 4: Parse the CSV data and extract URLs
        # GDELT CSV is tab-separated. Column 4 (0-indexed) is V2_GKG_REFERENCES,
        # which contains URLs.
        # This is a simplified parse. GDELT's schema is complex.
        # The relevant column for URLs is GKG_V2_URLS (position 16 in the current GKG 2.0 schema).
        # We need to explicitly read the CSV, it's tab-separated.

        # Use StringIO to treat the string content as a file
        csv_file = StringIO(gdelt_response.text)
        reader = csv.reader(csv_file, delimiter='\t')

        articles = []
        # GDELT GKG schema is complex, V2_GKG_REFERENCES (column 4) has source links.
        # GKG_V2_URLS is column 16. Let's aim for 16, but if it doesn't work, might need to adjust.
        # Source URL is typically in the 17th position (index 16) if using GKG_V2 schema.
        URL_COLUMN_INDEX = 16 # Based on GKG 2.0 schema (Source URL)

        # Skip header if present, though GDELT often doesn't have a header in raw files
        # For simplicity, we'll assume no header or handle it if we read full schema.
        
        # A more robust GDELT parser would handle the full schema:
        # http://data.gdeltproject.org/documentation/GDELT-GKG-Fieldbook.pdf

        for i, row in enumerate(reader):
            if i >= limit:
                break
            try:
                # GDELT rows can be very long. Check if the URL column exists.
                if len(row) > URL_COLUMN_INDEX:
                    # GKG V2_GKG_REFERENCES (Column 4) is also useful for source links.
                    # GKG_V2_URLS (Column 16) is more direct for article URLs.
                    article_url = row[URL_COLUMN_INDEX]
                    if article_url:
                        # GDELT can include multiple URLs or other data in this field
                        # Extract the first valid URL if multiple are present or it's complex.
                        # Simple split by comma for now, but often it's just one URL.
                        primary_url = article_url.split(',')[0].strip()
                        if primary_url.startswith("http"): # Basic URL validation
                            # Attempt to get a title, it's often in Column 2 (V2_GKG_TEXTUAL_DESCRIPTION)
                            title = row[2] if len(row) > 2 else "No Title Available"
                            articles.append({"title": title, "url": primary_url})
            except IndexError:
                # Row might be malformed or shorter than expected
                continue
            except Exception as e:
                print(f"Error parsing GDELT row {i}: {e}")
                continue

        return articles

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error fetching GDELT data: {e.response.text}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Network error or timeout fetching GDELT data: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while processing GDELT data: {e}"
        )

# --- Root Endpoint ---
@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to the News Aggregator API. Go to /docs for API documentation."}