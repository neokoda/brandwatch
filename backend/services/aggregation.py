import math
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from backend.models.mention import Mention
from backend.models.snapshot import SentimentSnapshot


def compute_engagement_score(likes: int = 0, shares: int = 0, comments: int = 0) -> float:
    return math.log(1 + likes + 2 * shares + 0.5 * comments)


async def upsert_snapshot(db: AsyncSession, mention: Mention) -> None:
    """Update or create the hourly snapshot bucket for a mention."""
    if mention.ingested_at is None:
        return

    hour_bucket = mention.ingested_at.replace(minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(SentimentSnapshot).where(
            and_(
                SentimentSnapshot.tracker_id == mention.tracker_id,
                SentimentSnapshot.hour_bucket == hour_bucket,
            )
        )
    )
    snap = result.scalar_one_or_none()

    if snap is None:
        snap = SentimentSnapshot(
            id=uuid.uuid4(),
            tracker_id=mention.tracker_id,
            hour_bucket=hour_bucket,
            source_channel=mention.source_channel,
            region_code=mention.region_code,
            language_code=mention.language_code,
            mention_count=0,
            positive_count=0,
            negative_count=0,
            neutral_count=0,
            avg_sentiment_score=0.0,
            avg_engagement=0.0,
        )
        db.add(snap)

    snap.mention_count = (snap.mention_count or 0) + 1
    if mention.sentiment_label == "positive":
        snap.positive_count = (snap.positive_count or 0) + 1
    elif mention.sentiment_label == "negative":
        snap.negative_count = (snap.negative_count or 0) + 1
    elif mention.sentiment_label == "neutral":
        snap.neutral_count = (snap.neutral_count or 0) + 1

    total = snap.mention_count
    prev_avg_sentiment = snap.avg_sentiment_score or 0.0
    prev_avg_engagement = snap.avg_engagement or 0.0
    snap.avg_sentiment_score = (prev_avg_sentiment * (total - 1) + (mention.sentiment_score or 0.0)) / total
    snap.avg_engagement = (prev_avg_engagement * (total - 1) + (mention.engagement_score or 0.0)) / total
