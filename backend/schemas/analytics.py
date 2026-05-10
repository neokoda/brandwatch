from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class KPIs(BaseModel):
    total_mentions: int
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_share: float
    negative_share: float
    avg_engagement: float
    active_alerts: int
    mentions_delta_pct: Optional[float] = None
    negative_delta_pct: Optional[float] = None


class TrendPoint(BaseModel):
    bucket: datetime
    total: int
    positive: int
    negative: int
    neutral: int
    avg_sentiment: float
    avg_engagement: float


class GeoPoint(BaseModel):
    region_code: str
    mention_count: int
    negative_share: float
    avg_sentiment: float


class SourceBreakdown(BaseModel):
    source_channel: str
    mention_count: int
    positive_count: int
    negative_count: int
    avg_engagement: float


class AuthorStat(BaseModel):
    author_name: str
    mention_count: int
    avg_sentiment: float
    is_influencer: bool
    total_engagement: float


class LanguageBreakdown(BaseModel):
    language_code: str
    mention_count: int
    positive_share: float


class EmotionStat(BaseModel):
    emotion_label: str
    count: int
    share: float
