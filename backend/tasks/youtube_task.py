"""YouTube Data API v3 ingestion — video search + comment threads."""
import uuid
import logging
import httpx
from backend.database import async_session_factory
from backend.config import settings

logger = logging.getLogger(__name__)

YT_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YT_COMMENTS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"


async def run_youtube_for_tracker(tracker_id: uuid.UUID):
    if not settings.YOUTUBE_API_KEY:
        return

    async with async_session_factory() as db:
        from sqlalchemy import select
        from backend.models.tracker import Tracker
        result = await db.execute(select(Tracker).where(Tracker.id == tracker_id, Tracker.is_active == True))  # noqa: E712
        tracker = result.scalar_one_or_none()
        from backend.tasks.task_utils import tracker_allows_source
        if not tracker or not tracker_allows_source(tracker, "youtube") or not tracker.keywords:
            return

        query = " ".join(tracker.keywords[:3])
        items_to_ingest = []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Search for relevant videos
                search_resp = await client.get(YT_SEARCH_URL, params={
                    "key": settings.YOUTUBE_API_KEY,
                    "q": query,
                    "part": "snippet",
                    "type": "video",
                    "maxResults": "10",
                    "order": "date",
                })
                search_resp.raise_for_status()
                videos = search_resp.json().get("items", [])

                for video in videos:
                    video_id = video.get("id", {}).get("videoId")
                    if not video_id:
                        continue

                    # Get comments
                    comments_resp = await client.get(YT_COMMENTS_URL, params={
                        "key": settings.YOUTUBE_API_KEY,
                        "videoId": video_id,
                        "part": "snippet",
                        "maxResults": "20",
                        "order": "relevance",
                    })
                    if comments_resp.status_code != 200:
                        continue
                    from backend.tasks.task_utils import strip_html, mention_matches_keywords
                    for thread in comments_resp.json().get("items", []):
                        top = thread.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                        like_count = top.get("likeCount", 0)
                        text = strip_html(top.get("textDisplay", ""))
                        if not text or not mention_matches_keywords(text, tracker.keywords):
                            continue
                        items_to_ingest.append({
                            "source_channel": "youtube",
                            "source_url": f"https://www.youtube.com/watch?v={video_id}&lc={thread.get('id', '')}",
                            "source_domain": "youtube.com",
                            "author_name": top.get("authorDisplayName"),
                            "author_id": top.get("authorChannelId", {}).get("value"),
                            "content_text": text,
                            "engagement_raw": {"likes": like_count},
                            "keywords_matched": [kw for kw in tracker.keywords if kw.lower() in text.lower()],
                            "raw_payload": thread,
                        })
        except Exception as exc:
            logger.warning("YouTube fetch error for tracker %s: %s", tracker_id, exc)
            return

        if not items_to_ingest:
            return

        from backend.schemas.mention import IngestRequest, MentionIngestItem
        from backend.services.ingestion import run_ingestion_pipeline
        payload = IngestRequest(
            tracker_id=tracker_id,
            mentions=[MentionIngestItem(**i) for i in items_to_ingest],
        )
        await run_ingestion_pipeline(db, payload)
        logger.info("YouTube: ingested %d comments for tracker %s", len(items_to_ingest), tracker_id)
