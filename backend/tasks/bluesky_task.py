"""Bluesky ingestion via public AT Protocol AppView API. No API key required."""
import uuid
import logging
import asyncio
from datetime import datetime, timezone
import httpx
from backend.database import async_session_factory

logger = logging.getLogger(__name__)

BSKY_SEARCH_URL = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"


async def run_bluesky_for_tracker(tracker_id: uuid.UUID):
    async with async_session_factory() as db:
        from sqlalchemy import select
        from backend.models.tracker import Tracker
        result = await db.execute(select(Tracker).where(Tracker.id == tracker_id, Tracker.is_active == True))  # noqa: E712
        tracker = result.scalar_one_or_none()
        if not tracker or not tracker.keywords:
            return

        items = []

        for keyword in tracker.keywords[:3]:
            await asyncio.sleep(1)
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    resp = await client.get(BSKY_SEARCH_URL, params={
                        "q": keyword,
                        "limit": 25,
                        "sort": "latest",
                    })
                    if resp.status_code == 400:
                        logger.info("Bluesky search returned 400 for %r (no results)", keyword)
                        continue
                    resp.raise_for_status()
                    posts = resp.json().get("posts", [])
            except Exception as exc:
                logger.warning("Bluesky fetch error for tracker %s keyword %r: %s", tracker_id, keyword, exc)
                continue

            for post in posts:
                record = post.get("record", {})
                author = post.get("author", {})
                cid = post.get("cid", "")
                uri = post.get("uri", "")
                handle = author.get("handle", "")
                rkey = uri.split("/")[-1] if "/" in uri else cid
                post_url = f"https://bsky.app/profile/{handle}/post/{rkey}" if handle and rkey else ""

                text = record.get("text", "")
                if not text.strip():
                    continue

                created_raw = record.get("createdAt")
                published_at = None
                if created_raw:
                    try:
                        published_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                    except ValueError:
                        pass

                viewer = post.get("viewer", {})
                like_count = post.get("likeCount", 0) or 0
                reply_count = post.get("replyCount", 0) or 0
                repost_count = post.get("repostCount", 0) or 0

                items.append({
                    "source_channel": "bluesky",
                    "source_url": post_url or f"https://bsky.app/profile/{handle}",
                    "source_domain": "bsky.app",
                    "author_name": author.get("displayName") or handle,
                    "author_id": author.get("did"),
                    "author_follower_count": author.get("followersCount"),
                    "content_text": text[:2000],
                    "published_at": published_at,
                    "engagement_raw": {"likes": like_count, "shares": repost_count, "comments": reply_count},
                    "keywords_matched": [keyword],
                    "raw_payload": {"cid": cid, "uri": uri},
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
        logger.info("Bluesky: ingested %d posts for tracker %s", len(items), tracker_id)
