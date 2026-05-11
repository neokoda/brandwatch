import logging
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.alert import Alert, CrossChannelInsight
from backend.models.tracker import Tracker
from backend.services.gemini import gemma_chat

logger = logging.getLogger(__name__)


async def generate_cross_channel_insight(db: AsyncSession, account_id: uuid.UUID) -> CrossChannelInsight | None:
    """Detect correlated signals across trackers and generate a Gemma 4 narrative."""
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

    tracker_result = await db.execute(select(Tracker).where(Tracker.id.in_(tracker_ids)))
    trackers = {t.id: t.name for t in tracker_result.scalars().all()}

    insight_text = await _gemma_insight(alerts, trackers) or _local_insight(alerts, trackers)

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


async def _gemma_insight(alerts: list, trackers: dict) -> str | None:
    summary = "\n".join(
        f"- {trackers.get(a.tracker_id, '?')}: {a.title} ({a.severity})"
        for a in alerts
    )
    return await gemma_chat(
        messages=[
            {
                "role": "system",
                "content": "You are a brand intelligence analyst. Identify patterns across multiple brand tracking alerts.",
            },
            {
                "role": "user",
                "content": (
                    f"These alerts fired concurrently across different trackers:\n{summary}\n\n"
                    "Provide a 2-3 sentence cross-channel narrative explaining the likely common cause "
                    "and recommended action. Reply with only the narrative — no preamble."
                ),
            },
        ],
        max_tokens=300,
        temperature=0.5,
    )


def _local_insight(alerts: list, trackers: dict) -> str:
    names = [trackers.get(a.tracker_id, str(a.tracker_id)) for a in alerts]
    alert_types = list({a.alert_type for a in alerts})
    return (
        f"Concurrent alerts detected across {', '.join(set(names))}. "
        f"Alert types: {', '.join(alert_types)}. "
        "Review these trackers together as they may share a common cause."
    )
