import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.topic import TopicCluster
from backend.models.tracker import Tracker
from backend.schemas.topic import TopicClusterOut

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=List[TopicClusterOut])
async def list_topics(
    tracker_id: Optional[uuid.UUID] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(TopicCluster)
        .join(Tracker, TopicCluster.tracker_id == Tracker.id)
        .where(Tracker.account_id == current_user.account_id)
        .order_by(TopicCluster.mention_count.desc())
    )
    if tracker_id:
        q = q.where(TopicCluster.tracker_id == tracker_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/recluster", status_code=202)
async def recluster(
    background_tasks: BackgroundTasks,
    tracker_id: Optional[uuid.UUID] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if tracker_id:
        tr = await db.execute(
            select(Tracker).where(Tracker.id == tracker_id, Tracker.account_id == current_user.account_id)
        )
        if not tr.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Tracker not found")
        from backend.services.topic_clustering import recluster_tracker
        background_tasks.add_task(_run_recluster, tracker_id)
    else:
        trackers_result = await db.execute(
            select(Tracker.id).where(Tracker.account_id == current_user.account_id, Tracker.is_active == True)  # noqa: E712
        )
        for (tid,) in trackers_result.all():
            background_tasks.add_task(_run_recluster, tid)
    return {"status": "queued"}


async def _run_recluster(tracker_id: uuid.UUID):
    from backend.database import async_session_factory
    from backend.services.topic_clustering import recluster_tracker
    async with async_session_factory() as db:
        await recluster_tracker(db, tracker_id)


@router.get("/{topic_id}/mentions")
async def topic_mentions(
    topic_id: uuid.UUID,
    page: int = 1,
    page_size: int = 25,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from backend.models.mention import Mention
    from backend.schemas.mention import MentionOut
    result = await db.execute(
        select(Mention)
        .join(Tracker, Mention.tracker_id == Tracker.id)
        .where(Mention.topic_cluster_id == topic_id, Tracker.account_id == current_user.account_id)
        .order_by(Mention.ingested_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    mentions = result.scalars().all()
    return [MentionOut.model_validate(m) for m in mentions]
