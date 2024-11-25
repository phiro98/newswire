from typing import Optional
from typing import Optional, List
from pydantic import BaseModel, Field

# Pydantic schema for request validation
class NewsEntrySchema(BaseModel):
    name: str = Field(..., example="Example News")
    url: str = Field(..., example="https://example.com/news")
    news_count: int = Field(..., example=10)
    auto_dialer: bool = Field(..., example=True)
    author: Optional[str] = Field(None, example="Author Name")
    categories: List[str] = Field(None, example=["Category1", "Category2"])
    tags: List[str] = Field(None, example=["Tag1", "Tag2"])
    delay: Optional[int] = Field(None, example=5)

    class Config:
        from_attributes = True

# Pydantic model for input validation
class NewsEntryUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Name of the news entry")
    url: Optional[str] = Field(None, description="URL of the news entry")
    news_count: Optional[int] = Field(None, description="Number of news items to fetch")
    auto_dialer: Optional[bool] = Field(None, description="Auto dialer status")
    author: Optional[str] = Field(None, description="Author of the news entry")
    categories: Optional[List[str]] = Field(None, description="List of categories")
    tags: Optional[List[str]] = Field(None, description="List of tags")
    delay: Optional[int] = Field(None, description="Delay in hours")
