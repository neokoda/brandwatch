import logging
import uuid
from datetime import datetime, timedelta, timezone
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.account import Account
from backend.models.alert import Alert, CrossChannelInsight
from backend.models.tracker import Tracker

logger = logging.getLogger(__name__)


async def generate_cross_channel_insight(db: AsyncSession, account_id: uuid.UUID) -> CrossChannelInsight | None:
    """Detect correlated signals across trackers and call the agent for a narrative."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=4)

    result = await db.execute(
        select(Alert)
        .where(Alert.account_id == account_id)
        .where(Alert.is_resolved == False)  # noqa: E712
        .where(Alert.triggered_at >= cutoff)
        .where(Alert.tracker_id.isnot(None))
    )
    alerts = result.scalars().all()

    tracker_ids = list({a.tracker_id for a in alerts})
    if len(tracker_ids) < 2:
        return None

    # Get tracker names
    tracker_result = await db.execute(
        select(Tracker).where(Tracker.id.in_(tracker_ids))
    )
    trackers = {t.id: t.name for t in tracker_result.scalars().all()}

    account_result = await db.execute(select(Account).where(Account.id == account_id))
    account = account_result.scalar_one_or_none()
    if not account or not account.agent_webhook_url:
        insight_text = _build_local_insight(alerts, trackers)
    else:
        insight_text = await _call_agent(account, alerts, trackers)

    if not insight_text:
        return None

    insight = CrossChannelInsight(
        id=uuid.uuid4(),
        account_id=account_id,
        insight_text=insight_text,
        related_tracker_ids=[str(tid) for tid in tracker_ids],
        related_alert_ids=[str(a.id) for a in alerts],
    )
    db.add(insight)
    await db.commit()
    return insight


def _build_local_insight(alerts: list, trackers: dict) -> str:
    names = [trackers.get(a.tracker_id, str(a.tracker_id)) for a in alerts]
    alert_types = list({a.alert_type for a in alerts})
    return (
        f"Concurrent alerts detected across {', '.join(set(names))}. "
        f"Alert types: {', '.join(alert_types)}. "
        "Review these trackers together as they may share a common cause."
    )


async def _call_agent(account: Account, alerts: list, trackers: dict) -> str | None:
    summary = "\n".join(
        f"- {trackers.get(a.tracker_id, '?')}: {a.title} ({a.severity})"
        for a in alerts
    )
    payload = {
        "model": "hermes",
        "messages": [
            {"role": "system", "content": "You are a brand intelligence analyst. Identify patterns across multiple brand tracking alerts."},
            {"role": "user", "content": f"These alerts fired concurrently across different trackers:\n{summary}\n\nProvide a 2-3 sentence cross-channel narrative explaining the likely common cause and recommended action."},
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
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("Cross-channel agent call failed: %s", exc)
        return _build_local_insight(alerts, trackers)
