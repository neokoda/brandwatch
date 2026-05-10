"""Mastodon ingestion via public search API on mastodon.social. No API key required."""
import uuid
import logging
import asyncio
from datetime import datetime, timezone
import httpx
from backend.database import async_session_factory

logger = logging.getLogger(__name__)

# mastodon.social is the largest instance and has an open public search API
MASTODON_SEARCH_URL = "https://mastodon.social/api/v2/search"


async def run_mastodon_for_tracker(tracker_id: uuid.UUID):
    async with async_session_factory() as db:
        from sqlalchemy import select
        from backend.models.tracker import Tracker
        result = await db.execute(select(Tracker).where(Tracker.id == tracker_id, Tracker.is_active == True))  # noqa: E712
        tracker = result.scalar_one_or_none()
        from backend.tasks.task_utils import tracker_allows_source
        if not tracker or not tracker_allows_source(tracker, "mastodon") or not tracker.keywords:
            return

        items = []

        for keyword in tracker.keywords[:3]:
            await asyncio.sleep(2)
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    resp = await client.get(MASTODON_SEARCH_URL, params={
                        "q": keyword,
                        "type": "statuses",
                        "limit": 20,
                        "resolve": "false",
                    })
                    resp.raise_for_status()
                    statuses = resp.json().get("statuses", [])
            except Exception as exc:
                logger.warning("Mastodon fetch error for tracker %s keyword %r: %s", tracker_id, keyword, exc)
                continue

            for status in statuses:
                # Strip HTML tags from content
                import re
                content_html = status.get("content", "")
                content_text = re.sub(r"<[^>]+>", " ", content_html).strip()
                content_text = re.sub(r"\s+", " ", content_text)[:2000]
                if not content_text.strip():
                    continue

                account = status.get("account", {})
                post_url = status.get("url", "")

                created_raw = status.get("created_at")
                published_at = None
                if created_raw:
                    try:
                        published_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                    except ValueError:
                        pass

                items.append({
                    "source_channel": "mastodon",
                    "source_url": post_url,
                    "source_domain": "mastodon.social",
                    "author_name": account.get("display_name") or account.get("username"),
                    "author_id": account.get("id"),
                    "author_follower_count": account.get("followers_count"),
                    "content_text": content_text,
                    "published_at": published_at,
                    "engagement_raw": {
                        "likes": status.get("favourites_count", 0) or 0,
                        "shares": status.get("reblogs_count", 0) or 0,
                        "comments": status.get("replies_count", 0) or 0,
                    },
                    "keywords_matched": [keyword],
                    "raw_payload": {"status_id": status.get("id")},
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
        logger.info("Mastodon: ingested %d posts for tracker %s", len(items), tracker_id)
