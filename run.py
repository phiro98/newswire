from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi.middleware.cors import CORSMiddleware


# Database setup
DATABASE_URL = "sqlite:///./news.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy model for news_entry
class NewsEntry(Base):
    __tablename__ = "news_entry"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    url = Column(String)
    news_count = Column(Integer)
    auto_dialer = Column(Boolean)
    author = Column(String, nullable=True)
    categories = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    delay = Column(Integer, nullable=True)
    delay_unit = Column(String, nullable=True)

# Create the database tables
Base.metadata.create_all(bind=engine)

# Pydantic schema for request validation
class NewsEntrySchema(BaseModel):
    name: str = Field(..., example="Example News")
    url: str = Field(..., example="https://example.com/news")
    news_count: int = Field(..., example=10)
    auto_dialer: bool = Field(..., example=True)
    
    # Optional fields
    author: Optional[str] = Field(None, example="Author Name")
    categories: Optional[List[str]] = Field(None, example=["Category1", "Category2"])
    tags: Optional[List[str]] = Field(None, example=["Tag1", "Tag2"])
    delay: Optional[int] = Field(None, example=5)
    delay_unit: Optional[str] = Field(None, example="minutes")

    class Config:
        orm_mode = True


app = FastAPI()

# Allow requests from the frontend running on localhost:8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# POST endpoint to create a new news entry
@app.post("/news_entry/")
def create_news_entry(news_entry: NewsEntrySchema, db: SessionLocal = Depends(get_db)):
    # Create the news entry
    entry = NewsEntry(
        name=news_entry.name,
        url=news_entry.url,
        news_count=news_entry.news_count,
        auto_dialer=news_entry.auto_dialer,
        author=news_entry.author,
        categories=",".join(news_entry.categories) if news_entry.categories else None,
        tags=",".join(news_entry.tags) if news_entry.tags else None,
        delay=news_entry.delay,
        delay_unit=news_entry.delay_unit,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    
    return {"message": "News entry created", "data": entry}

# GET endpoint to retrieve all news entries
@app.get("/news_entries/")
def get_news_entries(db: SessionLocal = Depends(get_db)):
    entries = db.query(NewsEntry).all()
    return [
        {
            "id": entry.id,
            "name": entry.name,
            "url": entry.url,
            "news_count": entry.news_count,
            "auto_dialer": entry.auto_dialer,
            "author": entry.author,
            "categories": entry.categories.split(',') if entry.categories else [],
            "tags": entry.tags.split(',') if entry.tags else [],
            "delay": entry.delay,
            "delay_unit": entry.delay_unit
        }
        for entry in entries
    ]

# Run the application
# Use the command below to run the server if you're running this as a script.
# uvicorn main:app --reload
