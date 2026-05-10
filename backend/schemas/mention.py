from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class MentionIngestItem(BaseModel):
    source_channel: str
    source_url: str
    source_domain: Optional[str] = None
    author_name: Optional[str] = None
    author_id: Optional[str] = None
    author_follower_count: int = 0
    region_code: Optional[str] = None
    language_code: Optional[str] = None
    content_text: str
    published_at: Optional[datetime] = None
    engagement_raw: dict = {}
    keywords_matched: List[str] = []
    raw_payload: dict = {}


class IngestRequest(BaseModel):
    tracker_id: uuid.UUID
    mentions: List[MentionIngestItem]


class MentionOut(BaseModel):
    id: uuid.UUID
    tracker_id: uuid.UUID
    tracker_name: Optional[str] = None
    source_channel: str
    source_url: str
    source_domain: Optional[str]
    author_name: Optional[str]
    is_influencer: bool
    region_code: Optional[str]
    language_code: Optional[str]
    content_text: str
    content_excerpt: Optional[str]
    published_at: Optional[datetime]
    ingested_at: datetime
    engagement_score: float
    sentiment_label: str
    sentiment_score: float
    emotion_label: Optional[str]
    topic_cluster_id: Optional[uuid.UUID]
    topic_label: Optional[str] = None
    triage_status: str
    triage_priority: Optional[str]
    triage_assignee: Optional[str]
    triage_note: Optional[str]
    keywords_matched: List[str]

    model_config = {"from_attributes": True}


class MentionTriageUpdate(BaseModel):
    triage_status: Optional[str] = None
    triage_priority: Optional[str] = None
    triage_assignee: Optional[str] = None
    triage_note: Optional[str] = None


class MentionListResponse(BaseModel):
    items: List[MentionOut]
    total: int
    page: int
    page_size: int
