"""Apple App Store review ingestion via iTunes Search + RSS JSON API. No auth required."""
import uuid
import logging
import asyncio
from datetime import datetime, timezone
import httpx
from backend.database import async_session_factory

logger = logging.getLogger(__name__)

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
ITUNES_RSS_URL = "https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"


async def run_appstore_for_tracker(tracker_id: uuid.UUID):
    async with async_session_factory() as db:
        from sqlalchemy import select
        from backend.models.tracker import Tracker
        result = await db.execute(select(Tracker).where(Tracker.id == tracker_id, Tracker.is_active == True))  # noqa: E712
        tracker = result.scalar_one_or_none()
        from backend.tasks.task_utils import tracker_allows_source
        if not tracker or not tracker_allows_source(tracker, "appstore") or not tracker.keywords:
            return

        items = []
        seen_app_ids: set[str] = set()

        async with httpx.AsyncClient(timeout=20) as client:
            for keyword in tracker.keywords[:3]:
                # Search for matching apps
                try:
                    search_resp = await client.get(ITUNES_SEARCH_URL, params={
                        "term": keyword,
                        "entity": "software",
                        "limit": 3,
                        "country": "us",
                    })
                    search_resp.raise_for_status()
                    app_results = search_resp.json().get("results", [])
                except Exception as exc:
                    logger.warning("App Store search error for %r: %s", keyword, exc)
                    continue

                for app in app_results:
                    app_id = str(app.get("trackId", ""))
                    if not app_id or app_id in seen_app_ids:
                        continue
                    seen_app_ids.add(app_id)
                    await asyncio.sleep(1)

                    # Fetch reviews via iTunes RSS JSON
                    try:
                        rss_url = ITUNES_RSS_URL.format(country="us", app_id=app_id)
                        rss_resp = await client.get(rss_url, headers={
                            "User-Agent": "Mozilla/5.0",
                        })
                        if rss_resp.status_code != 200 or not rss_resp.text.strip():
                            continue
                        feed = rss_resp.json()
                    except Exception as exc:
                        logger.warning("App Store RSS error for app %s: %s", app_id, exc)
                        continue

                    entries = feed.get("feed", {}).get("entry", [])
                    if not entries:
                        continue

                    # First entry is app metadata, skip it
                    for entry in entries[1:]:
                        title = entry.get("title", {}).get("label", "")
                        content = entry.get("content", {}).get("label", "")
                        full_text = f"{title}. {content}".strip(". ") if title else content
                        if not full_text.strip():
                            continue
                        from backend.tasks.task_utils import mention_matches_keywords
                        if not mention_matches_keywords(full_text, tracker.keywords):
                            continue

                        updated_raw = entry.get("updated", {}).get("label", "")
                        published_at = None
                        if updated_raw:
                            try:
                                published_at = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
                            except ValueError:
                                pass

                        author = entry.get("author", {}).get("name", {}).get("label", "")
                        review_id = entry.get("id", {}).get("label", "")

                        items.append({
                            "source_channel": "appstore",
                            "source_url": f"https://apps.apple.com/us/app/id{app_id}",
                            "source_domain": "apps.apple.com",
                            "author_name": author or None,
                            "content_text": full_text[:2000],
                            "published_at": published_at,
                            "engagement_raw": {},
                            "keywords_matched": [keyword],
                            "raw_payload": {
                                "app_id": app_id,
                                "app_name": app.get("trackName"),
                                "rating": entry.get("im:rating", {}).get("label"),
                                "review_id": review_id,
                            },
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
        logger.info("AppStore: ingested %d reviews for tracker %s", len(items), tracker_id)
