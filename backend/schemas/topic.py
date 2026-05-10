from __future__ import annotations
import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel


class TopicClusterOut(BaseModel):
    id: uuid.UUID
    tracker_id: uuid.UUID
    label: str
    keywords: List[str]
    mention_count: int
    sentiment_avg: float
    period_start: datetime
    period_end: datetime

    model_config = {"from_attributes": True}


class ReclusterRequest(BaseModel):
    tracker_id: uuid.UUID
