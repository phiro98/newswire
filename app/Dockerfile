# # # Use an official Python runtime as a parent image
# # FROM python:3.11-slim

# # # Set the working directory in the container
# # WORKDIR /app

# # # Copy the requirements.txt file into the container
# # COPY requirements.txt .

# # # Install any needed packages specified in requirements.txt
# # RUN pip install --no-cache-dir -r requirements.txt

# # # Copy the rest of the app's code into the container
# # COPY . .

# # # Expose the port FastAPI runs on
# # EXPOSE 8000

# # # Command to run the FastAPI app with Uvicorn
# # CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


# #################MULTISTAGE################
# # Stage 1: Build stage
# FROM python:3.11-slim AS builder

# # Set the working directory
# WORKDIR /app

# # Copy the requirements file to install dependencies
# COPY requirements.txt .

# # Install dependencies in a temporary directory (to keep the final image lean)
# RUN pip install --no-cache-dir --target=/install -r requirements.txt


# # Stage 2: Final stage (production)
# FROM python:3.11-slim

# # Set the working directory
# WORKDIR /app

# # Copy only the dependencies from the build stage
# COPY --from=builder /install /usr/local/lib/python3.11/site-packages

# # Copy the rest of the application code
# COPY . .

# # Expose the port FastAPI will run on
# EXPOSE 8000

# # Command to run the FastAPI app with Uvicorn
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


########### multistage 2 #################

# Stage 1: Build Stage with Alpine
FROM python:3.11-alpine AS builder

# Set environment variables to minimize Docker image size
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install dependencies required to build (including build tools)
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

# Copy the requirements file
COPY requirements.txt .

# Install dependencies in a temporary directory
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: Final Stage (smaller runtime)
FROM python:3.11-alpine

# Set environment variables to minimize Docker image size
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install the minimal dependencies for runtime
RUN apk add --no-cache libffi libgcc openssl

# Copy the installed dependencies from the builder
COPY --from=builder /install /usr/local

# Copy the FastAPI application code
COPY . .

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run the FastAPI app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
