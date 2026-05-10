"""Topic recluster job — runs every 6 hours via APScheduler."""
import logging
from backend.database import async_session_factory

logger = logging.getLogger(__name__)


async def run_recluster_all():
    async with async_session_factory() as db:
        from sqlalchemy import select
        from backend.models.tracker import Tracker
        from backend.services.topic_clustering import recluster_tracker
        result = await db.execute(select(Tracker.id).where(Tracker.is_active == True))  # noqa: E712
        for (tracker_id,) in result.all():
            try:
                n = await recluster_tracker(db, tracker_id)
                logger.info("Reclustered %d topics for tracker %s", n, tracker_id)
            except Exception as exc:
                logger.warning("Recluster error for tracker %s: %s", tracker_id, exc)
