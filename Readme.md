
# FastAPI Newswire Application

This is a FastAPI-based application that manages and schedules news entries. You can run this application using either the shell or Docker.
## Requirements- Python 3.11+- FastAPI- Uvicorn- Docker (if running with Docker)
## Running Locally with Shell

To run this FastAPI application locally on your machine, follow these steps:
### 1. Clone the repository
```bash
git clone https://github.com/phiro98/newswire
cd app
```
### 2. Set up a Virtual Environment (optional but recommended)
```bash
python3 -m venv newsenv
source newsenv/bin/activate
export FIREBASE_KEY="/mnt/c/Users/CN/Desktop/newswire/firebase_key.json"
export PROJECT_ID=newswire-2cd3b
```
### 3. Install dependencies
Make sure to install all required dependencies from requirements.txt:


```bash
pip install -r requirements.txt
```
### 4. Run the application with Uvicorn
Once dependencies are installed, you can run the FastAPI app using Uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000

```
This will start the FastAPI app at http://localhost:8000.
## Running with Docker
You can also run the application using Docker. The Docker image phiro98/newswire:latest is available on DockerHub.

### 1. Pull the Docker Image
To pull the image from DockerHub, use the following command:
```bash
docker pull phiro98/newswire:latest
```
### 2. Run the Docker Container
Once the image is pulled, you can run the container:

```bash
docker run -d -p 8000:8000 phiro98/newswire:latest
```
This will start the FastAPI app inside a Docker container, exposing it on port 8000. You can access the app at http://localhost:8000.

### 3. View Running Containers
To check if the container is running, use the following command:
```bash
docker ps
```
## API Endpoints
### 1. Create a News Entry
- URL: /news_entry/
- Method: POST
- Description: Create a new news entry.
- Request Body:json
```json
{
  "name": "Example News",
  "url": "https://example.com/news",
  "news_count": 10,
  "auto_dialer": true,
  "author": "Author Name",
  "categories": ["Category1", "Category2"],
  "tags": ["Tag1", "Tag2"],
  "delay": 5
}
```
### 2. Schedule a Task
- URL: /schedule_task/{id}
- Method: POST
- Description: Schedule a task for the news entry with the given id.

### 3. View All Tasks
- URL: /tasks
- Method: GET
- Description: view all upcoming tasks

### 4. Fetch RSS Feed
- URL: /fetch_feed/{id}
- Method: GET
- Description: fetch given number of news from the given rss feed URL

### 5. Fetch Scheduled Fetch Data
- URL: /job_result
- Method: GET
- Description: show the fetched with scheduled task
## License
This project is licensed under the MIT License.




