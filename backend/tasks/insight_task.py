"""Cross-channel insight job — runs every 2 hours via APScheduler."""
import logging
from backend.database import async_session_factory

logger = logging.getLogger(__name__)


async def run_insights_all():
    async with async_session_factory() as db:
        from sqlalchemy import select
        from backend.models.account import Account
        from backend.services.cross_channel import generate_cross_channel_insight
        result = await db.execute(select(Account.id))
        for (account_id,) in result.all():
            try:
                insight = await generate_cross_channel_insight(db, account_id)
                if insight:
                    logger.info("Cross-channel insight generated for account %s", account_id)
            except Exception as exc:
                logger.warning("Insight error for account %s: %s", account_id, exc)
