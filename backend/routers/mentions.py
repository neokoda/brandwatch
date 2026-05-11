import uuid
import asyncio
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.auth import get_current_user, get_current_user_from_token
from backend.models.mention import Mention
from backend.models.tracker import Tracker
from backend.models.topic import TopicCluster
from backend.schemas.mention import MentionOut, MentionTriageUpdate, MentionListResponse

router = APIRouter(prefix="/mentions", tags=["mentions"])
logger = logging.getLogger(__name__)


@router.get("", response_model=MentionListResponse)
async def list_mentions(
    tracker_id: Optional[uuid.UUID] = None,
    sentiment: Optional[str] = None,
    source: Optional[str] = None,
    triage_status: Optional[str] = None,
    is_influencer: Optional[bool] = None,
    language: Optional[str] = None,
    region: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base = (
        select(Mention)
        .join(Tracker, Mention.tracker_id == Tracker.id)
        .where(Tracker.account_id == current_user.account_id)
        .order_by(Mention.ingested_at.desc())
    )

    if tracker_id:
        base = base.where(Mention.tracker_id == tracker_id)
    if sentiment:
        base = base.where(Mention.sentiment_label == sentiment)
    if source:
        base = base.where(Mention.source_channel == source)
    if triage_status:
        base = base.where(Mention.triage_status == triage_status)
    if is_influencer is not None:
        base = base.where(Mention.is_influencer == is_influencer)
    if language:
        base = base.where(Mention.language_code == language)
    if region:
        base = base.where(Mention.region_code == region)
    if search:
        base = base.where(Mention.content_text.ilike(f"%{search}%"))
    if date_from:
        base = base.where(Mention.published_at >= date_from)
    if date_to:
        base = base.where(Mention.published_at <= date_to)

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    paginated = base.offset(offset).limit(page_size)
    result = await db.execute(paginated)
    mentions = result.scalars().all()

    # Batch-fetch tracker names and topic labels — avoids N+1 queries
    tracker_ids = list({m.tracker_id for m in mentions})
    topic_ids = list({m.topic_cluster_id for m in mentions if m.topic_cluster_id})

    tracker_names: dict = {}
    if tracker_ids:
        tr = await db.execute(select(Tracker.id, Tracker.name).where(Tracker.id.in_(tracker_ids)))
        tracker_names = {row[0]: row[1] for row in tr.all()}

    topic_labels: dict = {}
    if topic_ids:
        tl = await db.execute(select(TopicCluster.id, TopicCluster.label).where(TopicCluster.id.in_(topic_ids)))
        topic_labels = {row[0]: row[1] for row in tl.all()}

    items = []
    for m in mentions:
        item = MentionOut.model_validate(m)
        item.tracker_name = tracker_names.get(m.tracker_id)
        item.topic_label = topic_labels.get(m.topic_cluster_id) if m.topic_cluster_id else None
        items.append(item)

    return MentionListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/stream")
async def mention_stream(
    token: str,
    tracker_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """SSE endpoint. JWT passed via query param since EventSource can't set headers."""
    current_user = await get_current_user_from_token(token, db)

    async def event_generator():
        last_id_sent = None
        while True:
            try:
                query = (
                    select(Mention)
                    .join(Tracker, Mention.tracker_id == Tracker.id)
                    .where(Tracker.account_id == current_user.account_id)
                    .order_by(Mention.ingested_at.desc())
                    .limit(5)
                )
                if tracker_id:
                    query = query.where(Mention.tracker_id == tracker_id)

                result = await db.execute(query)
                mentions = result.scalars().all()

                for m in reversed(mentions):
                    if last_id_sent is None or m.id != last_id_sent:
                        last_id_sent = m.id
                        data = {
                            "id": str(m.id),
                            "source_channel": m.source_channel,
                            "content_excerpt": m.content_excerpt,
                            "sentiment_label": m.sentiment_label,
                            "ingested_at": m.ingested_at.isoformat(),
                        }
                        import json
                        yield f"data: {json.dumps(data)}\n\n"
            except Exception as exc:
                logger.warning("SSE error: %s", exc)

            await asyncio.sleep(10)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{mention_id}", response_model=MentionOut)
async def get_mention(
    mention_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import outerjoin
    row = await db.execute(
        select(Mention, Tracker.name.label("tracker_name"), TopicCluster.label.label("topic_label"))
        .join(Tracker, Mention.tracker_id == Tracker.id)
        .outerjoin(TopicCluster, Mention.topic_cluster_id == TopicCluster.id)
        .where(Mention.id == mention_id, Tracker.account_id == current_user.account_id)
    )
    result = row.first()
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Mention not found")

    mention, tracker_name, topic_label = result
    out = MentionOut.model_validate(mention)
    out.tracker_name = tracker_name
    out.topic_label = topic_label
    return out


@router.patch("/{mention_id}/triage", response_model=MentionOut)
async def update_triage(
    mention_id: uuid.UUID,
    body: MentionTriageUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Mention)
        .join(Tracker, Mention.tracker_id == Tracker.id)
        .where(Mention.id == mention_id, Tracker.account_id == current_user.account_id)
    )
    mention = result.scalar_one_or_none()
    if not mention:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Mention not found")

    from datetime import timezone
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(mention, field, value)
    mention.triage_updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(mention)
    return MentionOut.model_validate(mention)


@router.post("/{mention_id}/draft-reply")
async def draft_reply(
    mention_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Mention)
        .join(Tracker, Mention.tracker_id == Tracker.id)
        .where(Mention.id == mention_id, Tracker.account_id == current_user.account_id)
    )
    mention = result.scalar_one_or_none()
    if not mention:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Mention not found")

    from backend.services.agent import draft_mention_reply
    draft = await draft_mention_reply(db, mention, current_user.account_id)
    return {"draft_reply": draft}
