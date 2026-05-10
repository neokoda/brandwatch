from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class TrackerCreate(BaseModel):
    name: str
    tracker_type: str = "brand"
    keywords: List[str] = []
    languages: List[str] = []
    regions: List[str] = []
    rss_feeds: List[str] = []


class TrackerUpdate(BaseModel):
    name: Optional[str] = None
    tracker_type: Optional[str] = None
    keywords: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    rss_feeds: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TrackerOut(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    name: str
    tracker_type: str
    keywords: List[str]
    languages: List[str]
    regions: List[str]
    rss_feeds: List[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
