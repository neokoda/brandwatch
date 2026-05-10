from __future__ import annotations
import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel


class InsightOut(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    insight_text: str
    related_tracker_ids: List[str]
    related_alert_ids: List[str]
    generated_at: datetime

    model_config = {"from_attributes": True}
