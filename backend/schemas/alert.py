from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AlertOut(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    tracker_id: Optional[uuid.UUID]
    tracker_name: Optional[str] = None
    alert_type: str
    severity: str
    title: str
    description: str
    metric_value: Optional[float]
    metric_baseline: Optional[float]
    triggered_at: datetime
    is_resolved: bool
    resolved_at: Optional[datetime]
    agent_notified: bool
    draft_response: Optional[str]

    model_config = {"from_attributes": True}


class AlertResolveRequest(BaseModel):
    pass


class DraftResponseRequest(BaseModel):
    pass
