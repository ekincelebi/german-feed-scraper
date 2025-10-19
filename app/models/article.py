from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class Article(BaseModel):
    """Article model matching the Supabase schema."""

    id: UUID = Field(default_factory=uuid4)
    url: str
    title: str
    content: Optional[str] = None
    published_date: Optional[datetime] = None
    author: Optional[str] = None
    source_feed: Optional[str] = None
    source_domain: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class Feed(BaseModel):
    """Feed model matching the Supabase schema."""

    id: UUID = Field(default_factory=uuid4)
    url: str
    domain: Optional[str] = None
    last_fetched: Optional[datetime] = None
    status: str = "active"
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
