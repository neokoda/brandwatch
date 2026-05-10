import uuid
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.tracker import Tracker
from backend.schemas.tracker import TrackerCreate, TrackerUpdate, TrackerOut

router = APIRouter(prefix="/trackers", tags=["trackers"])


@router.get("", response_model=List[TrackerOut])
async def list_trackers(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Tracker).where(Tracker.account_id == current_user.account_id)
    )
    return result.scalars().all()


@router.post("", response_model=TrackerOut, status_code=status.HTTP_201_CREATED)
async def create_tracker(
    body: TrackerCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tracker = Tracker(id=uuid.uuid4(), account_id=current_user.account_id, **body.model_dump())
    db.add(tracker)
    await db.commit()
    await db.refresh(tracker)
    return tracker


@router.get("/{tracker_id}", response_model=TrackerOut)
async def get_tracker(
    tracker_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tracker = await _get_owned_tracker(tracker_id, current_user.account_id, db)
    return tracker


@router.put("/{tracker_id}", response_model=TrackerOut)
async def update_tracker(
    tracker_id: uuid.UUID,
    body: TrackerUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tracker = await _get_owned_tracker(tracker_id, current_user.account_id, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(tracker, field, value)
    await db.commit()
    await db.refresh(tracker)
    return tracker


@router.delete("/{tracker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tracker(
    tracker_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tracker = await _get_owned_tracker(tracker_id, current_user.account_id, db)
    await db.delete(tracker)
    await db.commit()


@router.post("/{tracker_id}/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_tracker(
    tracker_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tracker = await _get_owned_tracker(tracker_id, current_user.account_id, db)
    from backend.tasks.gdelt_task import run_gdelt_for_tracker
    background_tasks.add_task(run_gdelt_for_tracker, tracker_id)
    return {"status": "queued", "tracker_id": str(tracker_id)}


async def _get_owned_tracker(tracker_id: uuid.UUID, account_id: uuid.UUID, db: AsyncSession) -> Tracker:
    result = await db.execute(
        select(Tracker).where(Tracker.id == tracker_id, Tracker.account_id == account_id)
    )
    tracker = result.scalar_one_or_none()
    if not tracker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tracker not found")
    return tracker
