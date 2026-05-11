import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.alert import CrossChannelInsight
from backend.schemas.insight import InsightOut

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=List[InsightOut])
async def list_insights(
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CrossChannelInsight)
        .where(CrossChannelInsight.account_id == current_user.account_id)
        .order_by(CrossChannelInsight.generated_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/generate", status_code=202)
async def generate_insight(
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    """Queue insight generation. Frontend should poll GET /insights until a new entry appears."""
    queued_at = datetime.now(timezone.utc).isoformat()
    background_tasks.add_task(_run_insight, current_user.account_id)
    return {"status": "queued", "queued_at": queued_at}


async def _run_insight(account_id: uuid.UUID):
    from backend.database import async_session_factory
    from backend.services.cross_channel import generate_cross_channel_insight
    async with async_session_factory() as db:
        await generate_cross_channel_insight(db, account_id)
