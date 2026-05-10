"""Google Play Store review ingestion via google-play-scraper."""
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from backend.database import async_session_factory

logger = logging.getLogger(__name__)


def _search_apps_sync(keyword: str) -> list[str]:
    """Search Play Store for apps matching keyword. Returns list of app IDs."""
    try:
        from google_play_scraper import search
        results = search(keyword, lang="en", country="us", n_hits=3)
        return [r["appId"] for r in results]
    except Exception as exc:
        logger.warning("Play Store app search error for %r: %s", keyword, exc)
        return []


def _fetch_reviews_sync(app_id: str) -> list[dict]:
    """Fetch recent reviews for a Play Store app."""
    try:
        from google_play_scraper import reviews, Sort
        result, _ = reviews(app_id, lang="en", country="us", sort=Sort.NEWEST, count=20)
        return result
    except Exception as exc:
        logger.warning("Play Store reviews error for app %r: %s", app_id, exc)
        return []


async def run_playstore_for_tracker(tracker_id: uuid.UUID):
    async with async_session_factory() as db:
        from sqlalchemy import select
        from backend.models.tracker import Tracker
        result = await db.execute(select(Tracker).where(Tracker.id == tracker_id, Tracker.is_active == True))  # noqa: E712
        tracker = result.scalar_one_or_none()
        from backend.tasks.task_utils import tracker_allows_source
        if not tracker or not tracker_allows_source(tracker, "playstore") or not tracker.keywords:
            return

        loop = asyncio.get_event_loop()
        items = []
        seen_app_ids: set[str] = set()

        for keyword in tracker.keywords[:3]:
            app_ids = await loop.run_in_executor(None, _search_apps_sync, keyword)
            for app_id in app_ids:
                if app_id in seen_app_ids:
                    continue
                seen_app_ids.add(app_id)
                await asyncio.sleep(1)
                raw_reviews = await loop.run_in_executor(None, _fetch_reviews_sync, app_id)

                from backend.tasks.task_utils import mention_matches_keywords
                for review in raw_reviews:
                    text = (review.get("content") or "").strip()
                    if not text or not mention_matches_keywords(text, tracker.keywords):
                        continue

                    at = review.get("at")
                    published_at = None
                    if isinstance(at, datetime):
                        published_at = at.replace(tzinfo=timezone.utc) if at.tzinfo is None else at

                    review_id = review.get("reviewId", "")
                    items.append({
                        "source_channel": "playstore",
                        "source_url": f"https://play.google.com/store/apps/details?id={app_id}&reviewId={review_id}",
                        "source_domain": "play.google.com",
                        "author_name": review.get("userName"),
                        "author_id": review.get("userImage"),
                        "content_text": text[:2000],
                        "published_at": published_at,
                        "engagement_raw": {"likes": review.get("thumbsUpCount", 0) or 0},
                        "keywords_matched": [keyword],
                        "raw_payload": {"app_id": app_id, "score": review.get("score"), "review_id": review_id},
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
        logger.info("PlayStore: ingested %d reviews for tracker %s", len(items), tracker_id)
