import csv
import io
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.auth import get_current_user, get_current_user_from_token, bearer_scheme
from backend.models.mention import Mention
from backend.models.tracker import Tracker

router = APIRouter(prefix="/export", tags=["export"])


async def _resolve_user(
    token: Optional[str],
    credentials: Optional[HTTPAuthorizationCredentials],
    db: AsyncSession,
):
    """Accept JWT either as ?token= query param (browser download) or Authorization header."""
    if token:
        return await get_current_user_from_token(token, db)
    if credentials:
        return await get_current_user(credentials, db)
    raise HTTPException(status_code=401, detail="Not authenticated")


@router.get("/mentions.csv")
async def export_mentions_csv(
    token: Optional[str] = Query(None),
    tracker_id: Optional[uuid.UUID] = None,
    days: int = 30,
    sentiment: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    language: Optional[str] = None,
    region: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _resolve_user(token, credentials, db)

    q = (
        select(Mention)
        .join(Tracker, Mention.tracker_id == Tracker.id)
        .where(Tracker.account_id == current_user.account_id)
        .order_by(Mention.ingested_at.desc())
        .limit(5000)
    )
    if tracker_id:
        q = q.where(Mention.tracker_id == tracker_id)
    if sentiment:
        q = q.where(Mention.sentiment_label == sentiment)
    if source:
        q = q.where(Mention.source_channel == source)
    if search:
        q = q.where(Mention.content_text.ilike(f"%{search}%"))
    if language:
        q = q.where(Mention.language_code == language)
    if region:
        q = q.where(Mention.region_code == region)
    if date_from:
        q = q.where(Mention.published_at >= date_from)
    if date_to:
        q = q.where(Mention.published_at <= date_to)
    if not date_from and not date_to:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        q = q.where(Mention.ingested_at >= since)

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
