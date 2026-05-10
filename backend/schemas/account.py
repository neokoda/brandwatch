from __future__ import annotations
import uuid
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AccountOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    agent_webhook_url: Optional[str]
    telegram_chat_id: Optional[str]
    alert_config: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    agent_webhook_url: Optional[str] = None
    agent_api_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    alert_config: Optional[dict] = None
