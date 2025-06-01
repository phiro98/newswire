from schemas.news_response import NewsItem
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import spacy

app = FastAPI()

# Load spaCy model for preprocessing
nlp = spacy.load("en_core_web_sm")

# Data model for articles
class Article(BaseModel):
    id: int
    text: str

class ArticleInput(BaseModel):
    articles: List[Article]

# Preprocessing function
def preprocess_text(text: str) -> str:
    doc = nlp(text.lower())
    processed_text = " ".join([token.lemma_ for token in doc if not token.is_stop and not token.is_punct])
    return processed_text

# Route to compare articles and cluster them
async def compare_and_cluster_articles(articles: NewsItem):
    texts = [article.text for article in articles]
    
    # Preprocess texts
    processed_texts = [preprocess_text(text) for text in texts]

    # TF-IDF Vectorization
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(processed_texts)

    # Cosine Similarity
    similarity_matrix = cosine_similarity(tfidf_matrix)

    # Clustering (KMeans)
    num_clusters = 3  # For now, we use 3 clusters; adjust based on need
    kmeans = KMeans(n_clusters=num_clusters)
    clusters = kmeans.fit_predict(tfidf_matrix)

    return {
        "similarity_matrix": similarity_matrix.tolist(),
        "clusters": clusters.tolist()
    }

# Test API endpoint
@app.get("/")
def read_root():
    return {"message": "Article Comparator is running!"}