# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker

# DATABASE_URL = "sqlite:///./news.db"
# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


import firebase_admin
from firebase_admin import credentials, firestore
import os
from utils import logger
# Replace with your service account key path. Download this from the Firebase console.
firebase_key_path=os.environ.get("FIREBASE_KEY")
projectId=os.environ.get("PROJECT_ID")
logger.info(f"firebase_key_path:: {firebase_key_path}")
cred = credentials.Certificate(firebase_key_path)
firebase_admin.initialize_app(cred, {
    'projectId': projectId,
})

db = firestore.client()