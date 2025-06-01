from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
# from database import engine
Base = declarative_base()

class NewsEntry(Base):
    __tablename__ = "news_entry"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    url = Column(String)
    news_count = Column(Integer, default=2)
    auto_dialer = Column(Boolean)
    author = Column(String, nullable=True)
    categories = Column(Text, nullable=True)  # Will store as JSON string
    tags = Column(Text, nullable=True)  # Will store as JSON string
    delay = Column(Integer, nullable=True, default=1)

# Create the database tables
Base.metadata.create_all(bind=engine)