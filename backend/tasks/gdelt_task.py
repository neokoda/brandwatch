"""GDELT ingestion: queries the GDELT 2.0 DOC API, no API key needed."""
import uuid
import logging
import asyncio
from urllib.parse import quote
import httpx
from backend.database import async_session_factory

logger = logging.getLogger(__name__)

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# GDELT returns full language names; map to ISO 639-1 codes
_GDELT_LANG_MAP = {
    "english": "en", "french": "fr", "german": "de", "spanish": "es",
    "portuguese": "pt", "italian": "it", "dutch": "nl", "russian": "ru",
    "arabic": "ar", "chinese": "zh", "japanese": "ja", "korean": "ko",
    "hindi": "hi", "thai": "th", "turkish": "tr", "polish": "pl",
    "swedish": "sv", "norwegian": "no", "danish": "da", "finnish": "fi",
    "indonesian": "id", "malay": "ms", "romanian": "ro", "ukrainian": "uk",
    "czech": "cs", "hungarian": "hu", "greek": "el", "hebrew": "he",
    "vietnamese": "vi", "persian": "fa",
}


async def run_gdelt_for_tracker(tracker_id: uuid.UUID):
    async with async_session_factory() as db:
        from sqlalchemy import select
        from backend.models.tracker import Tracker
        result = await db.execute(select(Tracker).where(Tracker.id == tracker_id, Tracker.is_active == True))  # noqa: E712
        tracker = result.scalar_one_or_none()
        from backend.tasks.task_utils import tracker_allows_source
        if not tracker or not tracker_allows_source(tracker, "gdelt") or not tracker.keywords:
            return

        keyword_query = " OR ".join(f'"{kw}"' for kw in tracker.keywords[:5])

        params = {
            "query": keyword_query,
            "mode": "artlist",
            "maxrecords": "75",
            "format": "json",
            "timespan": "30min",  # short window so each run sees fresh articles; dedup filters overlap
        }

        data = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(GDELT_URL, params=params)
                    text = resp.text.strip()
                    # GDELT sometimes returns rate-limit text with 200 status
                    if resp.status_code == 429 or "limit requests" in text.lower():
                        wait = 10 * (attempt + 1)
                        logger.info("GDELT rate limited, waiting %ds (attempt %d/3)", wait, attempt + 1)
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    if not text:
                        logger.info("GDELT returned empty body for tracker %s", tracker_id)
                        return
                    data = resp.json()
                    break
            except Exception as exc:
                logger.warning("GDELT fetch error for tracker %s: %s", tracker_id, exc)
                return
        if data is None:
            logger.warning("GDELT gave up after 3 attempts for tracker %s", tracker_id)
            return

        articles = data.get("articles") or []
        if not articles:
            return

        from backend.schemas.mention import IngestRequest, MentionIngestItem
        from backend.services.ingestion import run_ingestion_pipeline

        items = []
        for article in articles:
            items.append(MentionIngestItem(
                source_channel="gdelt",
                source_url=article.get("url", ""),
                source_domain=article.get("domain", ""),
                author_name=article.get("domain", ""),
                region_code=article.get("sourcecountry") or None,
                language_code=_GDELT_LANG_MAP.get((article.get("sourcelang") or "").lower()) or None,
                content_text=article.get("title", "") + " " + article.get("seendatetime", ""),
                keywords_matched=tracker.keywords,
                raw_payload=article,
            ))

        if items:
            payload = IngestRequest(tracker_id=tracker_id, mentions=items)
            await run_ingestion_pipeline(db, payload)
            logger.info("GDELT: ingested %d articles for tracker %s", len(items), tracker_id)
