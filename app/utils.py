import requests
import xmltodict
import json
from datetime import datetime
from bs4 import BeautifulSoup
import lxml

#global variable for storing schedular data
SCHED_FEED = []
# Fetch XML, convert to JSON, and save to file
def fetch_rss(url,news_count,task_id = 0):
    try:
        data = requests.get(url)

        if data.status_code == 200:
            newsSoup = BeautifulSoup(data.content,'xml')
            entries = newsSoup.find_all('item')
            entries = entries[:news_count]
            # List to hold all news items
            news_items = []
            for entry in entries:
                title = entry.title.text
                pub_date = entry.pubDate.text
                guid = entry.guid.text
                link = entry.link.text
                description = entry.description.text
                creator = entry.find('dc:creator').text if entry.find('dc:creator') else "No creator"
                category = entry.category.text if entry.find('category') else "No category"
                if entry.find('media:thumbnail'):
                    media = entry.find('media:thumbnail')['url']  
                elif entry.find('enclosure'):
                    media = entry.find('enclosure')['url']  
                else: "No thumbnail"
                # Append the data as a dictionary
                news_items.append({
                    "title": title,
                    "link": link,
                    "published_date": pub_date,
                    "creator": creator,
                    "category": category,
                    "description": description,
                    "guid": guid,
                    "media": media
                })
                
            # Return the list of news items as a JSON object
            if task_id:
                print(len(SCHED_FEED))
                SCHED_FEED.append(news_items)
            else:
                return json.dumps(news_items, indent=4)
    except:
        # Return error message if request failed
        return json.dumps({"error": "Failed to fetch RSS feed", "status_code": data.status_code}, indent=4)    

def clear_sched_feed():
    global SCHED_FEED
    SCHED_FEED.clear()
    print("list cleared")
fetch_rss("http://rss.cnn.com/rss/money_news_international.rss",13)
# fetch_and_save_xml("https://news.abplive.com/india/feed",5)