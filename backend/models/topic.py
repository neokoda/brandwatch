import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Float, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base

if TYPE_CHECKING:
    from backend.models.mention import Mention


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TopicCluster(Base):
    __tablename__ = "topic_clusters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tracker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trackers.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    label_raw: Mapped[Optional[str]] = mapped_column(String(500))
    keywords: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_avg: Mapped[float] = mapped_column(Float, default=0.0)
    dominant_sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    mentions: Mapped[List["Mention"]] = relationship("Mention", back_populates="topic_cluster")
