import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base

if TYPE_CHECKING:
    from backend.models.account import Account
    from backend.models.mention import Mention


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tracker(Base):
    __tablename__ = "trackers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tracker_type: Mapped[str] = mapped_column(String(50), default="brand")  # brand|keyword|hashtag|competitor|campaign
    keywords: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    languages: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    regions: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    rss_feeds: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    # Empty list = all sources enabled. Non-empty = only listed sources run.
    sources: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    account: Mapped["Account"] = relationship("Account", back_populates="trackers")
    mentions: Mapped[List["Mention"]] = relationship("Mention", back_populates="tracker", cascade="all, delete-orphan")
