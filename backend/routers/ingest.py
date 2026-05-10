"""
Ingestion endpoint — called by n8n workflows and APScheduler tasks.
Delegates to the shared run_ingestion_pipeline service.
"""
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.snapshot import IngestionRun
from backend.models.tracker import Tracker
from backend.schemas.mention import IngestRequest
from backend.services.ingestion import run_ingestion_pipeline

router = APIRouter(prefix="/ingest", tags=["ingest"])
logger = logging.getLogger(__name__)


@router.post("/mentions", status_code=status.HTTP_201_CREATED)
async def ingest_mentions(
    body: IngestRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await run_ingestion_pipeline(db, body)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/runs")
async def list_runs(
    tracker_id: uuid.UUID | None = None,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import join
    query = (
        select(IngestionRun)
        .join(Tracker, IngestionRun.tracker_id == Tracker.id)
        .where(Tracker.account_id == current_user.account_id)
        .order_by(IngestionRun.started_at.desc())
        .limit(limit)
    )
    if tracker_id:
        query = query.where(IngestionRun.tracker_id == tracker_id)
    result = await db.execute(query)
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "tracker_id": str(r.tracker_id),
            "source": r.source,
            "status": r.status,
            "mentions_found": r.mentions_found,
            "mentions_stored": r.mentions_stored,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "error_message": r.error_message,
        }
        for r in runs
    ]
