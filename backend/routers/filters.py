import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.snapshot import SavedFilter

router = APIRouter(prefix="/filters", tags=["filters"])


class FilterCreate(BaseModel):
    name: str
    tracker_id: Optional[uuid.UUID] = None
    filter_params: dict = {}


@router.get("")
async def list_filters(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SavedFilter).where(SavedFilter.account_id == current_user.account_id)
    )
    filters = result.scalars().all()
    return [{"id": str(f.id), "name": f.name, "filter_params": f.filter_params} for f in filters]


@router.post("", status_code=201)
async def create_filter(
    body: FilterCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    f = SavedFilter(
        id=uuid.uuid4(),
        account_id=current_user.account_id,
        name=body.name,
        tracker_id=body.tracker_id,
        filter_params=body.filter_params,
        created_by=current_user.email,
    )
    db.add(f)
    await db.commit()
    return {"id": str(f.id), "name": f.name}


@router.delete("/{filter_id}", status_code=204)
async def delete_filter(
    filter_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedFilter).where(SavedFilter.id == filter_id, SavedFilter.account_id == current_user.account_id)
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Filter not found")
    await db.delete(f)
    await db.commit()
