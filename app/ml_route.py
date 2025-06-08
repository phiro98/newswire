from schemas.news_response import NewsResponse as NewsItem
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import spacy
import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt


# Load spaCy model for preprocessing
nlp = spacy.load("en_core_web_sm")

# Preprocessing function
def preprocess_text(text: str) -> str:
    doc = nlp(text.lower())
    processed_text = " ".join([token.lemma_ for token in doc if not token.is_stop and not token.is_punct])
    return processed_text

# Route to compare articles and cluster them
async def compare_and_cluster_articles():
    # Read CSV and extract 'content' column
    df = pd.read_csv("news_data.csv")
    if 'content' not in df.columns:
        raise ValueError("CSV must contain a 'content' column")

    texts = df['content'].dropna().tolist()

    # Preprocess texts
    processed_texts = [preprocess_text(text) for text in texts]

    # TF-IDF Vectorization
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(processed_texts)

    # Get the feature names (i.e., words in the vocabulary)
    feature_names = vectorizer.get_feature_names_out()
    print(feature_names)
    print(tfidf_matrix.toarray())
    # Cosine Similarity
    similarity_matrix = cosine_similarity(tfidf_matrix)


    # Clustering (KMeans)
    num_clusters = 3  # For now, we use 3 clusters; adjust based on need
    kmeans = KMeans(n_clusters=num_clusters)
    clusters = kmeans.fit_predict(tfidf_matrix)
    # Make sure the directory exists
    os.makedirs('static', exist_ok=True)

    #similarity_heatmap
    plt.figure(figsize=(10, 8))
    sns.heatmap(similarity_matrix, cmap='coolwarm')
    plt.title("Article Similarity Heatmap")
    plt.savefig("static/similarity_heatmap.png")

    # PCA Clusters
    pca = PCA(n_components=2)
    reduced = pca.fit_transform(tfidf_matrix.toarray())
    plt.figure(figsize=(8, 6))
    plt.scatter(reduced[:, 0], reduced[:, 1], c=clusters, cmap='viridis')
    plt.title("Cluster Visualization (PCA)")
    plt.savefig("static/article_clusters.png")


    return {
        "similarity_matrix": similarity_matrix.tolist(),
        "clusters": clusters.tolist()
    }

