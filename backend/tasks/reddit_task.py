"""Reddit API ingestion via PRAW."""
import uuid
import logging
from backend.database import async_session_factory
from backend.config import settings

logger = logging.getLogger(__name__)


async def run_reddit_for_tracker(tracker_id: uuid.UUID):
    if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
        return

    async with async_session_factory() as db:
        from sqlalchemy import select
        from backend.models.tracker import Tracker
        result = await db.execute(select(Tracker).where(Tracker.id == tracker_id, Tracker.is_active == True))  # noqa: E712
        tracker = result.scalar_one_or_none()
        if not tracker or not tracker.keywords:
            return

        try:
            import praw
            reddit = praw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT,
            )
            query = " ".join(tracker.keywords[:3])
            submissions = list(reddit.subreddit("all").search(query, limit=25, time_filter="day"))
        except Exception as exc:
            logger.warning("Reddit fetch error for tracker %s: %s", tracker_id, exc)
            return

        items = []
        for sub in submissions:
            items.append({
                "source_channel": "reddit",
                "source_url": f"https://reddit.com{sub.permalink}",
                "source_domain": "reddit.com",
                "author_name": str(sub.author) if sub.author else None,
                "content_text": f"{sub.title} {sub.selftext}"[:2000],
                "engagement_raw": {"likes": sub.score, "comments": sub.num_comments},
                "keywords_matched": tracker.keywords,
                "raw_payload": {"subreddit": sub.subreddit.display_name, "score": sub.score},
            })

        if not items:
            return

        from backend.schemas.mention import IngestRequest, MentionIngestItem
        from backend.services.ingestion import run_ingestion_pipeline
        payload = IngestRequest(
            tracker_id=tracker_id,
            mentions=[MentionIngestItem(**i) for i in items],
        )
        await run_ingestion_pipeline(db, payload)
        logger.info("Reddit: ingested %d posts for tracker %s", len(items), tracker_id)
