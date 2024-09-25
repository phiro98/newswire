
# FastAPI Newswire Application

This is a FastAPI-based application that manages and schedules news entries. You can run this application using either the shell or Docker.## Requirements- Python 3.11+- FastAPI- Uvicorn- Docker (if running with Docker)## Running Locally with Shell

To run this FastAPI application locally on your machine, follow these steps:### 1. Clone the repository```bash
git clone <your-repository-url>
cd <your-repository-folder>
2. Set up a Virtual Environment (optional but recommended)
bash
Copy code
python3 -m venv venvsource venv/bin/activate
3. Install dependencies
Make sure to install all required dependencies from requirements.txt:


pip install -r requirements.txt
4. Run the application with Uvicorn
Once dependencies are installed, you can run the FastAPI app using Uvicorn:


uvicorn main:app --reload --host 0.0.0.0 --port 8000
This will start the FastAPI app at http://localhost:8000.
Running with Docker
You can also run the application using Docker. The Docker image phiro98/newswire:latest is available on DockerHub.

1. Pull the Docker Image
To pull the image from DockerHub, use the following command:

docker pull phiro98/newswire:latest
2. Run the Docker Container
Once the image is pulled, you can run the container:

docker run -d -p 8000:8000 phiro98/newswire:latest
This will start the FastAPI app inside a Docker container, exposing it on port 8000. You can access the app at http://localhost:8000.

3. View Running Containers
To check if the container is running, use the following command:

docker ps
API Endpoints
1. Create a News Entry
URL: /news_entry/
Method: POST
Description: Create a new news entry.
Request Body:json
Copy code
{
  "name": "Example News",
  "url": "https://example.com/news",
  "news_count": 10,
  "auto_dialer": true,
  "author": "Author Name",
  "categories": ["Category1", "Category2"],
  "tags": ["Tag1", "Tag2"],
  "delay": 5}
2. Schedule a Task
URL: /schedule/{id}
Method: POST
Description: Schedule a task for the news entry with the given id.
License
This project is licensed under the MIT License.



### Instructions:
- Replace `<your-repository-url>` and `<your-repository-folder>` with the actual repository URL and folder name.
- You can add more detailed descriptions about the project as needed.This `README.md` will guide users to run your FastAPI app either with Docker or in a Python environment. Let me know if you need any adjustments!

Here's a complete README.md file formatted with all necessary steps for running your FastAPI application using both shell and Docker.
