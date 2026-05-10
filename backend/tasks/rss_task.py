"""RSS feed ingestion using feedparser."""
import uuid
import logging
import feedparser
from datetime import datetime, timezone
from backend.database import async_session_factory

logger = logging.getLogger(__name__)


async def run_rss_for_tracker(tracker_id: uuid.UUID):
    async with async_session_factory() as db:
        from sqlalchemy import select
        from backend.models.tracker import Tracker
        result = await db.execute(select(Tracker).where(Tracker.id == tracker_id, Tracker.is_active == True))  # noqa: E712
        tracker = result.scalar_one_or_none()
        from backend.tasks.task_utils import tracker_allows_source, strip_html
        if not tracker or not tracker_allows_source(tracker, "rss") or not tracker.rss_feeds:
            return

        items = []
        for feed_url in tracker.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:20]:
                    published = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        import time
                        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                    content = strip_html(entry.get("summary", "") or "")
                    title = strip_html(entry.get("title", "") or "")
                    full_text = f"{title}. {content}"[:2000]

                    from urllib.parse import urlparse
                    domain = urlparse(entry.get("link", "")).netloc

                    items.append({
                        "source_channel": "rss",
                        "source_url": entry.get("link", feed_url),
                        "source_domain": domain,
                        "author_name": entry.get("author"),
                        "content_text": full_text,
                        "published_at": published,
                        "keywords_matched": tracker.keywords,
                        "raw_payload": {"feed": feed_url},
                    })
            except Exception as exc:
                logger.warning("RSS parse error for %s: %s", feed_url, exc)

        if not items:
            return

        from backend.schemas.mention import IngestRequest, MentionIngestItem
        from backend.services.ingestion import run_ingestion_pipeline
        payload = IngestRequest(
            tracker_id=tracker_id,
            mentions=[MentionIngestItem(**i) for i in items],
        )
        await run_ingestion_pipeline(db, payload)
        logger.info("RSS: ingested %d items for tracker %s", len(items), tracker_id)
