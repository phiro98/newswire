import requests
import xmltodict
import json
from datetime import datetime
from bs4 import BeautifulSoup
import lxml
import logging
from fastapi import Request
from functools import wraps
import os
import asyncio
from schemas.news_response import NewsItem, NewsResponse
from schemas.news_request import NewsEntrySchema
#global variable for storing schedular data
SCHED_FEED = []

# Ensure `logs` directory exists
if not os.path.exists("logs"):
    os.makedirs("logs")

# Setup basic logging configuration
log_file_path = "logs/app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()  # Optional: to also log to console
    ]
)
logger = logging.getLogger(__name__)

# Custom decorator to log request and response
def log_request_response(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # # Extract request object from FastAPI's args
        # request: Request = kwargs.get('Request')
        logger.info(f"Request:{kwargs}")  # Log the request
        # body = request.json()  # Log the request body if it exists
        # logger.info(f"Request: {request.method} {request.url}, Body: {body}")

        try:
            # Call the route function
            if asyncio.iscoroutinefunction(func):
                response = await func(*args, **kwargs)  # For async functions
            else:
                response = func(*args, **kwargs)  # For sync functions
            
            # Log the response data
            logger.info(f"Response: {response}")
            return response
        except Exception as e:
            logger.error(f"Exception occurred: {e}")
            raise e

    return wrapper

# Fetch XML, convert to JSON, and save to file
def fetch_rss(news_entry: NewsEntrySchema, task_id = 0):
    global SCHED_FEED
    try:
        logger.info(f"news_entry.url-->{news_entry.url}")
        data = requests.get(news_entry.url)

        if data.status_code == 200:
            newsSoup = BeautifulSoup(data.content,'xml')
            entries = newsSoup.find_all('item')
            entries = entries[:news_entry.news_count]
            # List to hold all news items
            news_items = []
            for entry in entries:
                logger.info(f"entry-->> {entry}")

                title = entry.title.text
                pub_date = entry.pubDate.text
                guide = entry.guid.text
                link = entry.link.text
                description = entry.description.text
                creator = entry.find('dc:creator').text if entry.find('dc:creator') else None
                category = entry.category.text if entry.find('category') else None
                if entry.find('media:thumbnail'):
                    media = entry.find('media:thumbnail')['url']  
                elif entry.find('enclosure'):
                    media = entry.find('enclosure')['url']  
                else: media = None
                # Append the data as a dictionary
                news_items.append(NewsItem(
                    title=title,
                    link=link,
                    published_date=pub_date,
                    creator=creator,
                    category=category,
                    description=description,
                    guid=guide,
                    media=media
                ))
            logger.info(f"cat:::{type(news_entry.categories)}")
            fetched_data = NewsResponse(
                name=news_entry.name, 
                categories=news_entry.categories, 
                tags=news_entry.tags, 
                news=news_items
            )
        logger.info(f"fetched_data::::{fetched_data}")
        # NewsResponse(name=news_entry.name, catagories=news_entry.categories, tags=news_entry.tags, news=news_items)
        
        SCHED_FEED.append(fetched_data)
        logger.info("array--->>>>>>",len(SCHED_FEED))
        if not task_id:
            return fetched_data            # Return the list of news items as a JSON object
    except Exception as e:
        logger.error(f"fetch_rss_err:: {e}")# Return error message if request failed
        # return json.dumps({"error": "Failed to fetch RSS feed", "status_code": data.status_code}, indent=4) 
        return json.dumps({"error": "Failed to fetch RSS feed", "status_code":400}, indent=4)    

def clear_sched_feed():
    global SCHED_FEED
    SCHED_FEED.clear()
    logger.info("list cleared")
# fetch_rss("http://rss.cnn.com/rss/money_news_international.rss",13)
# fetch_and_save_xml("https://news.abplive.com/india/feed",5)