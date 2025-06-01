import requests
from newsapi import NewsApiClient

# Init News API
newsapi = NewsApiClient(api_key='06b5860982864379bcb73fa663ed4365')  # Replace with your actual News API key

# Init Full Text RSS API details
full_text_rss_url = "https://full-text-rss.p.rapidapi.com/extract.php"
full_text_rss_headers = {
    "x-rapidapi-key": "180e620902msh188c96d4cd7f3fbp1eb4a7jsn9b38f26110b9",
    "x-rapidapi-host": "full-text-rss.p.rapidapi.com",
    "Content-Type": "application/x-www-form-urlencoded"
}

# Function to fetch full text from a URL
def get_full_text(article_url):
    payload = {
        "url": article_url,
        "xss": "1",
        "lang": "2",
        "links": "remove",
        "content": "1"
    }
    try:
        response = requests.post(full_text_rss_url, data=payload, headers=full_text_rss_headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching full text for {article_url}: {e}")
        return None

# Fetch top headlines about bitcoin
try:
    top_headlines = newsapi.get_top_headlines(q='bitcoin',
                                              language='en',
                                              category='business',
                                              country='us')

    if top_headlines['status'] == 'ok' and top_headlines['totalResults'] > 0:
        print(f"Processing top headlines...{top_headlines['totalResults']}")
        for article in top_headlines['articles']:
            article_url = article.get('url')
            if article_url:
                print(f"Fetching full text for: {article_url}")
                full_text_data = get_full_text(article_url)
                if full_text_data:
                    print("Full text data:")
                    print(full_text_data)
                    # You can now store the full_text_data as needed
                    print("-" * 20)
                else:
                    print("Failed to retrieve full text.")
                    print("-" * 20)
            else:
                print("Article URL not found.")
                print("-" * 20)
    else:
        print(f"Error fetching top headlines: {top_headlines['message']}")

except Exception as e:
    print(f"An error occurred while fetching top headlines: {e}")

# Fetch all articles about bitcoin within a date range (example)
# try:
#     all_articles = newsapi.get_everything(q='bitcoin',
#                                           sources='bbc-news,the-verge',
#                                           domains='bbc.co.uk,techcrunch.com',
#                                           from_param='2025-05-20',  # Adjusted date to be in the future
#                                           to='2025-05-27',    # Adjusted date to be today
#                                           language='en',
#                                           sort_by='relevancy',
#                                           page=1)  # Start from page 1

#     if all_articles['status'] == 'ok' and all_articles['totalResults'] > 0:
#         print("\nProcessing all articles...")
#         for article in all_articles['articles']:
#             article_url = article.get('url')
#             if article_url:
#                 print(f"Fetching full text for: {article_url}")
#                 full_text_data = get_full_text(article_url)
#                 if full_text_data:
#                     print("Full text data:")
#                     print(full_text_data)
#                     # You can now store the full_text_data as needed
#                     print("-" * 20)
#                 else:
#                     print("Failed to retrieve full text.")
#                     print("-" * 20)
#             else:
#                 print("Article URL not found.")
#                 print("-" * 20)
#     else:
#         print(f"Error fetching all articles: {all_articles.get('message', 'Unknown error')}")

# except Exception as e:
#     print(f"An error occurred while fetching all articles: {e}")

# # Note: The 'get_sources' endpoint doesn't provide article URLs,
# # so it's not included in the full-text fetching process.