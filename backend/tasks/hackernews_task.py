"""HackerNews ingestion via Algolia HN Search API. No API key required."""
import uuid
import logging
import asyncio
from datetime import datetime, timezone, timedelta
import httpx
from backend.database import async_session_factory

logger = logging.getLogger(__name__)

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


async def run_hackernews_for_tracker(tracker_id: uuid.UUID):
    async with async_session_factory() as db:
        from sqlalchemy import select
        from backend.models.tracker import Tracker
        result = await db.execute(select(Tracker).where(Tracker.id == tracker_id, Tracker.is_active == True))  # noqa: E712
        tracker = result.scalar_one_or_none()
        if not tracker or not tracker.keywords:
            return

        cutoff_ts = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
        items = []

        for keyword in tracker.keywords[:5]:
            await asyncio.sleep(1)  # be polite to Algolia
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    resp = await client.get(HN_SEARCH_URL, params={
                        "query": keyword,
                        "tags": "(story,comment)",
                        "numericFilters": f"created_at_i>{cutoff_ts}",
                        "hitsPerPage": 30,
                    })
                    resp.raise_for_status()
                    hits = resp.json().get("hits", [])
            except Exception as exc:
                logger.warning("HN fetch error for tracker %s keyword %r: %s", tracker_id, keyword, exc)
                continue

            for hit in hits:
                object_id = hit.get("objectID", "")
                item_type = "comment" if hit.get("parent_id") else "story"
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
                text = (hit.get("story_text") or hit.get("comment_text") or hit.get("title") or "")[:2000]
                if not text.strip():
                    continue

                created_raw = hit.get("created_at")
                published_at = None
                if created_raw:
                    try:
                        published_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                    except ValueError:
                        pass

                items.append({
                    "source_channel": "hackernews",
                    "source_url": url,
                    "source_domain": "news.ycombinator.com",
                    "author_name": hit.get("author"),
                    "content_text": text,
                    "published_at": published_at,
                    "engagement_raw": {"likes": hit.get("points") or 0, "comments": hit.get("num_comments") or 0},
                    "keywords_matched": [keyword],
                    "raw_payload": {"object_id": object_id, "type": item_type},
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
        logger.info("HackerNews: ingested %d items for tracker %s", len(items), tracker_id)
