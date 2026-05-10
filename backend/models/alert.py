import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Boolean, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    tracker_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("trackers.id", ondelete="CASCADE"), nullable=True)

    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # negativity_surge|volume_spike|crisis_risk|velocity_spike|cross_channel
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # info|warning|critical

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    metric_value: Mapped[Optional[float]] = mapped_column(Float)
    metric_baseline: Mapped[Optional[float]] = mapped_column(Float)
    threshold_used: Mapped[Optional[float]] = mapped_column(Float)

    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    agent_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    draft_response: Mapped[Optional[str]] = mapped_column(Text)


class CrossChannelInsight(Base):
    __tablename__ = "cross_channel_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    insight_text: Mapped[str] = mapped_column(Text, nullable=False)
    related_tracker_ids: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    related_alert_ids: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
