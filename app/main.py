# from ml import compare_and_cluster_articles
from schemas.news_response import NewsResponse
from fastapi import FastAPI, HTTPException, Depends 
# from sqlalchemy.orm import sessionmaker
from fastapi.middleware.cors import CORSMiddleware
from scheduler import scheduler, create_task
from sqlalchemy.orm import Session
import os
from utils import fetch_rss, SCHED_FEED, log_request_response, clear_sched_feed, logger
from schemas.news_request import NewsEntrySchema, NewsEntryUpdate
# from sqlalchemy import create_engine
from database import db
# from models.news_enrty import NewsEntry
# from sqlalchemy import create_engine, Column, Integer, String, Boolean
# from sqlalchemy.ext.declarative import declarative_base


app = FastAPI()

# Allow requests from the frontend running on localhost:8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# Initialize scheduler
scheduler.start()

# Route to add rssfeed
@app.post("/news_entry")
@log_request_response
def create_news_entry(news_entry: NewsEntrySchema):   #, db: SessionLocal = Depends(get_db)
    # Create the news entry
    try:
        # entry = NewsEntry(**news_entry.dict())
        #     name=news_entry.name,
        #     url=news_entry.url,
        #     news_count=news_entry.news_count,
        #     auto_dialer=news_entry.auto_dialer,
        #     author=news_entry.author,
        #     categories=",".join(news_entry.categories) if news_entry.categories else None,
        #     tags=",".join(news_entry.tags) if news_entry.tags else None,
        #     delay=news_entry.delay,
        # )
        logger.info(f"entry_details:: {news_entry.dict()}")
        doc_ref = db.collection("resourse_entry").document()
        doc_ref.set(news_entry.dict())        
        return {"message": "News entry created","task_id": doc_ref.id, "data": news_entry}
    except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# @app.get("/fetch_feed/{news_id}")
# @log_request_response
# def fetch_feed(news_id: int, db: SessionLocal = Depends(get_db)):
#     try:
#         task = db.query(NewsEntry).filter(NewsEntry.id == news_id).first()
#         feeds = fetch_rss(task)
#         return {"data":feeds}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# # @app.get("/compare_and_cluster/{news_id}")
# # @log_request_response
# # def compare_and_cluster(news_id: int, db: SessionLocal = Depends(get_db)):
# #     try:
# #         task = db.query(NewsEntry).filter(NewsEntry.id == news_id).first()
# #         feeds:NewsResponse = fetch_rss(task)
# #         cluster_data = compare_and_cluster_articles(feeds.news)
# #         return {"data":cluster_data}
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# @app.get("/fetch_all_entry/")
# @log_request_response
# def fetch_feed(db: SessionLocal = Depends(get_db)):
#     try:
#         news_data = db.query(NewsEntry).all()
#         newslist = [news for news in news_data]
#         return {"data":newslist}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# # Route to schedule a task by task id
# @app.post("/schedule_task/{task_id}")
# @log_request_response
# def schedule_task(news_id: int, db: SessionLocal = Depends(get_db)):
#     # Query the task from the database
#     task = db.query(NewsEntry).filter(NewsEntry.id == news_id).first()

#     # Check if task exists
#     if not task:
#         raise HTTPException(status_code=404, detail="Task not found")
#     if task.delay <= 0:
#         raise HTTPException(status_code=400, detail="Delay hours must be greater than zero")
#     # Run the create_task method (assuming it schedules a task)
#     try:
#         if task.auto_dialer:
#             task_id = create_task(task)   #task.url, task.delay, task.news_count)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

#     return {"message": "Task scheduled successfully", "task_id": task_id}

# @app.get("/tasks")
# @log_request_response
# def get_tasks():
#     try:
#         jobs = scheduler.get_jobs()
#         task_list = [{"task_id": job.id, "next_run_time": job.next_run_time} for job in jobs]
#         return {"tasks": task_list}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# # Ensure `data` directory exists
# if not os.path.exists("data"):
#     os.makedirs("data")

# @app.get("/job-result")
# @log_request_response
# def get_job_result():
#     global SCHED_FEED
#     try:    
#         if SCHED_FEED:
#             return SCHED_FEED  # Return the latest job output
#         return ["Job has not run yet"]
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    
# @app.delete("/delete-data")
# @log_request_response
# def delete_data_list():
#     global SCHED_FEED
#     try:    
#         if SCHED_FEED:
#             clear_sched_feed()
#         else: 
#             return {"data": "list is empty"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# # Route to update rssfeed
# @app.put("/news_entry/{news_id}")
# @log_request_response
# async def update_news_entry(news_id: int, update_data: NewsEntryUpdate, db: Session = Depends(get_db)):
#     try:
#         # Retrieve the existing NewsEntry record
#         news_entry = db.query(NewsEntry).filter(NewsEntry.id == news_id).first()
#         if not news_entry:
#             raise HTTPException(status_code=404, detail="News entry not found")

#         # Update only the fields that are provided
#         update_dict = update_data.dict(exclude_unset=True)
#         for key, value in update_dict.items():
#             if key == "categories":
#                 # Convert list to a comma-separated string if applicable
#                 logger.info(f"value: {value} {','.join(value)}")
#                 setattr(news_entry, key, ",".join(value) if value else None)
#             elif key == "tags":
#                 # Convert list to a comma-separated string if applicable
#                 setattr(news_entry, key, ",".join(value) if value else None)
#             else:
#                 setattr(news_entry, key, value)

#         # Save changes
#         db.add(news_entry)
#         db.commit()
#         db.refresh(news_entry)

#         return news_entry
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# @app.delete("/news_entry/{news_id}")
# def delete_news_entry(news_id: int, db: Session = Depends(get_db)):
#     try:
#         # Fetch the existing news entry
#         news_entry = db.query(NewsEntry).filter(NewsEntry.id == news_id).first()
#         if not news_entry:
#             raise HTTPException(status_code=404, detail="News entry not found")
        
#         # Delete the news entry
#         db.delete(news_entry)
#         db.commit()

#         return {"message": f"News entry with id {news_id} has been deleted successfully."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")