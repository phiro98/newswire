from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from utils import fetch_rss, clear_sched_feed

scheduler = BackgroundScheduler()

# Dictionary to track tasks
#dict of dict
tasks = {}

# Method to create a new scheduled task
def create_task(task: str):
    task_id = f"task_{len(tasks) + 1}"
    next_run_time = datetime.now() + timedelta(hours=task.delay)

    # Schedule the XML fetching job
    job = scheduler.add_job(fetch_rss, 'interval', hours=task.delay, args=[task,task_id], id=task_id, next_run_time=next_run_time)
    tasks[task_id] = {
        'url': task.url,
        'delay_hours': task.delay,
        'news_count': task.news_count,
        'next_run': next_run_time
    }

    return task_id

