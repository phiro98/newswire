from typing import Optional
from typing import Optional, List,Dict,Any
from pydantic import BaseModel, Field

class NewsResponse(BaseModel):
    name: str
    categories: List[str]
    tags: List[str]
    news: List[Dict[str,Any]]