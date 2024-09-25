from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from utils import fetch_rss, clear_sched_feed

scheduler = BackgroundScheduler()

# Dictionary to track tasks
#dict of dict
tasks = {}

# Method to create a new scheduled task
def create_task(url, delay_hours, news_count):
    task_id = f"task_{len(tasks) + 1}"
    next_run_time = datetime.now() + timedelta(minutes=delay_hours)

    # Schedule the XML fetching job
    job = scheduler.add_job(fetch_rss, 'interval', minutes=delay_hours, args=[url,news_count,task_id], id=task_id, next_run_time=next_run_time)
    tasks[task_id] = {
        'url': url,
        'delay_hours': delay_hours,
        'news_count': news_count,
        'next_run': next_run_time
    }

    return task_id

