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
    top_channel: str = ""


class LanguageBreakdown(BaseModel):
    language_code: str
    mention_count: int
    positive_share: float
    negative_share: float = 0.0


class VelocityData(BaseModel):
    current_rate: float       # mentions in last hour
    last_24h_mentions: int    # total mentions in last 24 hours
    baseline_rate: float      # avg mentions/hour over last 7 days (all hours incl. zeros)
    mentions_per_day: float   # baseline_rate * 24
    velocity_ratio: float     # current / baseline (>1 = faster, <1 = slower)
    trend: str                # "up" | "down" | "stable"
    current_negative_share: float
    baseline_negative_share: float
    negativity_z: float       # how many std devs above baseline negativity


class EmotionStat(BaseModel):
    emotion_label: str
    count: int
    share: float
