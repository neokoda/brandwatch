import csv
import io
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.mention import Mention
from backend.models.tracker import Tracker

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/mentions.csv")
async def export_mentions_csv(
    tracker_id: Optional[uuid.UUID] = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        select(Mention)
        .join(Tracker, Mention.tracker_id == Tracker.id)
        .where(Tracker.account_id == current_user.account_id, Mention.ingested_at >= since)
        .order_by(Mention.ingested_at.desc())
        .limit(5000)
    )
    if tracker_id:
        q = q.where(Mention.tracker_id == tracker_id)
    result = await db.execute(q)
    mentions = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "source_channel", "source_url", "author_name", "region_code",
        "language_code", "sentiment_label", "sentiment_score", "emotion_label",
        "engagement_score", "published_at", "ingested_at", "triage_status", "content_excerpt",
    ])
    for m in mentions:
        writer.writerow([
            str(m.id), m.source_channel, m.source_url, m.author_name, m.region_code,
            m.language_code, m.sentiment_label, m.sentiment_score, m.emotion_label,
            m.engagement_score, m.published_at, m.ingested_at, m.triage_status, m.content_excerpt,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mentions_export.csv"},
    )


@router.get("/summary.json")
async def export_summary_json(
    tracker_id: Optional[uuid.UUID] = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from backend.routers.analytics import kpis
    summary = await kpis(tracker_id=tracker_id, days=days, current_user=current_user, db=db)
    return summary
