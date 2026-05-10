"""Weekly digest — runs Monday 08:00 UTC. Calls each account's agent with a weekly summary."""
import logging
from datetime import datetime, timedelta, timezone
from backend.database import async_session_factory

logger = logging.getLogger(__name__)


async def run_weekly_digest():
    async with async_session_factory() as db:
        from sqlalchemy import select, func
        from backend.models.account import Account
        from backend.models.mention import Mention
        from backend.models.tracker import Tracker
        from backend.services.agent import notify_agent
        from backend.models.alert import Alert

        since = datetime.now(timezone.utc) - timedelta(days=7)
        accounts_result = await db.execute(select(Account))
        accounts = accounts_result.scalars().all()

        for account in accounts:
            if not account.agent_webhook_url:
                continue

            # Build weekly summary
            count_result = await db.execute(
                select(func.count(Mention.id))
                .join(Tracker, Mention.tracker_id == Tracker.id)
                .where(Tracker.account_id == account.id, Mention.ingested_at >= since)
            )
            total = count_result.scalar_one() or 0

            alert_result = await db.execute(
                select(func.count(Alert.id))
                .where(Alert.account_id == account.id, Alert.triggered_at >= since)
            )
            alert_count = alert_result.scalar_one() or 0

            if total == 0:
                continue

            import httpx
            payload = {
                "model": "hermes",
                "messages": [
                    {"role": "system", "content": "You are a brand intelligence analyst providing weekly summaries."},
                    {"role": "user", "content": f"Weekly digest for {account.name}:\n- {total} mentions this week\n- {alert_count} alerts triggered\n\nProvide a brief 2-3 sentence executive summary and top recommendation."},
                ],
                "max_tokens": 300,
            }
            headers = {"Content-Type": "application/json"}
            if account.agent_api_token:
                headers["Authorization"] = f"Bearer {account.agent_api_token}"
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(account.agent_webhook_url, json=payload, headers=headers)
                    resp.raise_for_status()
                    logger.info("Weekly digest sent for account %s", account.id)
            except Exception as exc:
                logger.warning("Digest send error for account %s: %s", account.id, exc)
