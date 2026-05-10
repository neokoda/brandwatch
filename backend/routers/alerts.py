import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.alert import Alert
from backend.models.tracker import Tracker
from backend.schemas.alert import AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=List[AlertOut])
async def list_alerts(
    tracker_id: Optional[uuid.UUID] = None,
    severity: Optional[str] = None,
    is_resolved: Optional[bool] = None,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Alert)
        .where(Alert.account_id == current_user.account_id)
        .order_by(Alert.triggered_at.desc())
        .limit(limit)
    )
    if tracker_id:
        q = q.where(Alert.tracker_id == tracker_id)
    if severity:
        q = q.where(Alert.severity == severity)
    if is_resolved is not None:
        q = q.where(Alert.is_resolved == is_resolved)

    result = await db.execute(q)
    alerts = result.scalars().all()

    out = []
    for a in alerts:
        tracker_name = None
        if a.tracker_id:
            tr = await db.execute(select(Tracker.name).where(Tracker.id == a.tracker_id))
            tracker_name = tr.scalar_one_or_none()
        item = AlertOut.model_validate(a)
        item.tracker_name = tracker_name
        out.append(item)
    return out


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(
    alert_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.account_id == current_user.account_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    tracker_name = None
    if alert.tracker_id:
        tr = await db.execute(select(Tracker.name).where(Tracker.id == alert.tracker_id))
        tracker_name = tr.scalar_one_or_none()
    out = AlertOut.model_validate(alert)
    out.tracker_name = tracker_name
    return out


@router.patch("/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(
    alert_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.account_id == current_user.account_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return AlertOut.model_validate(alert)


@router.post("/{alert_id}/draft-response")
async def draft_response(
    alert_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.account_id == current_user.account_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    from backend.services.agent import notify_agent
    draft = await notify_agent(db, alert)
    if draft:
        alert.draft_response = draft
        alert.agent_notified = True
        await db.commit()
    return {"draft_response": draft or alert.draft_response}
