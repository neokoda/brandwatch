import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, Float, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base

if TYPE_CHECKING:
    from backend.models.tracker import Tracker
    from backend.models.topic import TopicCluster


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Mention(Base):
    __tablename__ = "mentions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tracker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trackers.id", ondelete="CASCADE"), nullable=False)

    # Source metadata
    source_channel: Mapped[str] = mapped_column(String(20), nullable=False)  # gdelt|youtube|reddit|rss
    source_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_url_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256 for dedup
    source_domain: Mapped[Optional[str]] = mapped_column(String(255))

    # Author metadata
    author_name: Mapped[Optional[str]] = mapped_column(String(255))
    author_id: Mapped[Optional[str]] = mapped_column(String(255))
    author_follower_count: Mapped[int] = mapped_column(Integer, default=0)
    is_influencer: Mapped[bool] = mapped_column(Boolean, default=False)

    # Geographic / language
    region_code: Mapped[Optional[str]] = mapped_column(String(10))
    language_code: Mapped[Optional[str]] = mapped_column(String(10))

    # Content
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_excerpt: Mapped[Optional[str]] = mapped_column(String(500))

    # Timestamps
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Engagement
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    engagement_raw: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Sentiment
    sentiment_label: Mapped[str] = mapped_column(String(20), default="unclassified")  # positive|negative|neutral|unclassified
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_scores: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Emotion
    emotion_label: Mapped[Optional[str]] = mapped_column(String(50))
    emotion_score: Mapped[Optional[float]] = mapped_column(Float)

    # Topics
    topic_cluster_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("topic_clusters.id", ondelete="SET NULL"), nullable=True)
    keywords_matched: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Triage
    triage_status: Mapped[str] = mapped_column(String(20), default="new")  # new|in_review|resolved|dismissed
    triage_priority: Mapped[Optional[str]] = mapped_column(String(20))  # low|medium|high|critical
    triage_assignee: Mapped[Optional[str]] = mapped_column(String(255))
    triage_note: Mapped[Optional[str]] = mapped_column(Text)
    triage_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    is_alert_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)

    tracker: Mapped["Tracker"] = relationship("Tracker", back_populates="mentions")
    topic_cluster: Mapped[Optional["TopicCluster"]] = relationship("TopicCluster", back_populates="mentions")
