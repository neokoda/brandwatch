"""
Core ingestion pipeline extracted from the router so tasks can call it directly
without going through FastAPI's Depends() system.
"""
import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.mention import Mention
from backend.models.tracker import Tracker
from backend.models.alert import Alert
from backend.models.snapshot import IngestionRun
from backend.schemas.mention import IngestRequest
from backend.services.deduplication import compute_url_hash
from backend.services.influencer import is_influencer
from backend.services.language import detect_language
from backend.services.sentiment import classify_sentiment_batch, classify_emotion
from backend.services.aggregation import compute_engagement_score, upsert_snapshot
from backend.services.anomaly import check_anomalies
from backend.services.agent import notify_agent

logger = logging.getLogger(__name__)


async def run_ingestion_pipeline(db: AsyncSession, body: IngestRequest) -> dict:
    """Execute the full ingestion pipeline. Returns summary dict."""
    tracker_result = await db.execute(
        select(Tracker).where(Tracker.id == body.tracker_id, Tracker.is_active == True)  # noqa: E712
    )
    tracker = tracker_result.scalar_one_or_none()
    if not tracker:
        return {"error": "Tracker not found or inactive", "stored": 0}

    run = IngestionRun(
        id=uuid.uuid4(),
        tracker_id=body.tracker_id,
        source=body.mentions[0].source_channel if body.mentions else "unknown",
        status="running",
        mentions_found=len(body.mentions),
    )
    db.add(run)
    await db.flush()

    stored = 0
    new_mentions: list[Mention] = []
    texts_to_classify: list[tuple[int, str, str | None]] = []

    for item in body.mentions:
        if not item.source_url:
            continue
        url_hash = compute_url_hash(item.source_url)
        exists = await db.execute(
            select(Mention.id).where(
                Mention.source_url_hash == url_hash,
                Mention.tracker_id == body.tracker_id,
            )
        )
        if exists.scalar_one_or_none():
            continue

        lang = item.language_code or detect_language(item.content_text[:300])
        engagement = compute_engagement_score(
            likes=item.engagement_raw.get("likes", 0),
            shares=item.engagement_raw.get("shares", 0),
            comments=item.engagement_raw.get("comments", 0),
        )
        if engagement > 1.0:
            triage_priority = "high"
        elif engagement > 0:
            triage_priority = "medium"
        else:
            triage_priority = "low"

        mention = Mention(
            id=uuid.uuid4(),
            tracker_id=body.tracker_id,
            source_channel=item.source_channel,
            source_url=item.source_url,
            source_url_hash=url_hash,
            source_domain=item.source_domain,
            author_name=item.author_name,
            author_id=item.author_id,
            author_follower_count=item.author_follower_count,
            is_influencer=is_influencer(item.author_follower_count),
            region_code=item.region_code,
            language_code=lang,
            content_text=item.content_text,
            content_excerpt=item.content_text[:300],
            published_at=item.published_at,
            engagement_score=engagement,
            engagement_raw=item.engagement_raw,
            keywords_matched=item.keywords_matched,
            raw_payload=item.raw_payload,
            triage_priority=triage_priority,
        )
        db.add(mention)
        new_mentions.append(mention)
        texts_to_classify.append((len(new_mentions) - 1, item.content_text, lang))

    if not new_mentions:
        run.status = "success"
        run.mentions_stored = 0
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()
        return {"stored": 0, "skipped": len(body.mentions)}

    await db.flush()

    texts = [t for _, t, _ in texts_to_classify]
    first_lang = texts_to_classify[0][2] if texts_to_classify else None
    sentiment_results = await classify_sentiment_batch(texts, first_lang)

    for (idx, _, lang), sentiment in zip(texts_to_classify, sentiment_results):
        m = new_mentions[idx]
        m.sentiment_label = sentiment["label"]
        m.sentiment_score = sentiment["score"]
        m.sentiment_scores = sentiment["scores"]

        if lang == "en" and m.sentiment_label == "negative":
            emotion = await classify_emotion(m.content_text[:512])
            if emotion:
                m.emotion_label = emotion["label"]
                m.emotion_score = emotion["score"]

        await upsert_snapshot(db, m)
        stored += 1

    await db.flush()

    alert_dicts = await check_anomalies(db, body.tracker_id, tracker.account_id)
    new_alerts = []
    for ad in alert_dicts:
        alert = Alert(id=uuid.uuid4(), **ad)
        db.add(alert)
        new_alerts.append(alert)

    await db.flush()

    for alert in new_alerts:
        draft = await notify_agent(db, alert)
        if draft:
            alert.draft_response = draft
            alert.agent_notified = True

    run.status = "success"
    run.mentions_stored = stored
    run.finished_at = datetime.now(timezone.utc)
    await db.commit()

    return {"stored": stored, "skipped": len(body.mentions) - stored, "alerts_fired": len(new_alerts)}
