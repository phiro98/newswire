from typing import Optional
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    title: str
    link: str
    published_date: str
    creator: Optional[str] = None  # Optional field
    category: Optional[str] = None  # Optional field
    description: Optional[str] = None  # Optional field
    guid: str
    media: Optional[str] = None  # Optional field


class NewsResponse(BaseModel):
    name: str
    categories: Optional[List[str]] 
    tags: Optional[List[str]] 
    news: Optional[List[NewsItem]]