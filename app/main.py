from fastapi import FastAPI, HTTPException, Depends 
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi.middleware.cors import CORSMiddleware
from scheduler import scheduler, create_task
import os
from utils import fetch_rss, SCHED_FEED


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
    news_count = Column(Integer, default=2)
    auto_dialer = Column(Boolean)
    author = Column(String, nullable=True)
    categories = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    delay = Column(Integer, nullable=True, default=1)


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

    class Config:
        from_attributes = True


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



# Initialize scheduler
scheduler.start()

# Route to add rssfeed
@app.post("/news_entry")
def create_news_entry(news_entry: NewsEntrySchema, db: SessionLocal = Depends(get_db)):
    # Create the news entry
    try:
        entry = NewsEntry(
            name=news_entry.name,
            url=news_entry.url,
            news_count=news_entry.news_count,
            auto_dialer=news_entry.auto_dialer,
            author=news_entry.author,
            categories=",".join(news_entry.categories) if news_entry.categories else None,
            tags=",".join(news_entry.tags) if news_entry.tags else None,
            delay=news_entry.delay,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        
        return {"message": "News entry created","task_id": entry.id, "data": entry}
    except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@app.get("/fetch_feed/{news_id}")
def fetch_feed(news_id: int, db: SessionLocal = Depends(get_db)):
    try:
        task = db.query(NewsEntry).filter(NewsEntry.id == news_id).first()
        feeds = fetch_rss(task.url,task.news_count)
        return {"data":feeds}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@app.get("/fetch_all_entry/")
def fetch_feed(db: SessionLocal = Depends(get_db)):
    try:
        news_data = db.query(NewsEntry).all()
        newslist = [news for news in news_data]
        return {"data":newslist}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# Route to schedule a task by task id
@app.post("/schedule_task/{task_id}")
def schedule_task(task_id: int, db: SessionLocal = Depends(get_db)):
    # Query the task from the database
    task = db.query(NewsEntry).filter(NewsEntry.id == task_id).first()

    # Check if task exists
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.delay <= 0:
        raise HTTPException(status_code=400, detail="Delay hours must be greater than zero")
    # Run the create_task method (assuming it schedules a task)
    try:
        if task.auto_dialer:
            task_id = create_task(task.url, task.delay, task.news_count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    return {"message": "Task scheduled successfully", "task_id": task_id}

@app.get("/tasks")
def get_tasks():
    try:
        jobs = scheduler.get_jobs()
        task_list = [{"task_id": job.id, "next_run_time": job.next_run_time} for job in jobs]
        return {"tasks": task_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# Ensure `data` directory exists
if not os.path.exists("data"):
    os.makedirs("data")

@app.get("/job-result")
def get_job_result():
    global SCHED_FEED
    try:    
        if SCHED_FEED:
            return SCHED_FEED  # Return the latest job output
        return ["Job has not run yet"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    

