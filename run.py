#!/usr/bin/env python3
"""
Newswire Server Launcher
Starts the FastAPI application using Uvicorn.
"""
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"[*] Starting {settings.APP_NAME}...")
    print(f"[*] Dashboard UI: http://{settings.HOST}:{settings.PORT}/")
    print(f"[*] API Docs:     http://{settings.HOST}:{settings.PORT}/docs")
    print(f"[*] Database:     {settings.DATABASE_URL}")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1
    )
