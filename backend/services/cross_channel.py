import logging
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.alert import Alert, CrossChannelInsight
from backend.models.mention import Mention
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
    trackers: dict[uuid.UUID, Tracker] = {t.id: t for t in tracker_result.scalars().all()}

    # Fetch 3 recent negative mention excerpts per tracker for grounding
    tracker_excerpts: dict[uuid.UUID, list[str]] = {}
    for tid in tracker_ids:
        m_result = await db.execute(
            select(Mention.content_text)
            .where(Mention.tracker_id == tid, Mention.sentiment_label == "negative")
            .order_by(Mention.ingested_at.desc())
            .limit(3)
        )
        tracker_excerpts[tid] = [row[0][:200] for row in m_result.all()]

    insight_text = (
        await _gemma_insight(alerts, trackers, tracker_excerpts)
        or _local_insight(alerts, trackers)
    )

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


async def _gemma_insight(
    alerts: list,
    trackers: dict,
    tracker_excerpts: dict,
) -> str | None:
    lines = []
    seen_trackers: set = set()
    for a in alerts:
        t = trackers.get(a.tracker_id)
        t_name = t.name if t else "Unknown"
        t_kws = ", ".join((t.keywords or [])[:4]) if t else ""

        metric_str = ""
        if a.metric_value is not None and a.metric_baseline is not None:
            metric_str = f" | value={a.metric_value:.2f}, baseline={a.metric_baseline:.2f}"
        elif a.metric_value is not None:
            metric_str = f" | value={a.metric_value:.2f}"

        lines.append(
            f"Tracker: {t_name}"
            + (f" (keywords: {t_kws})" if t_kws else "")
            + f"\n  Alert: {a.title} [{a.severity}]{metric_str}"
        )

        if a.tracker_id not in seen_trackers:
            excerpts = tracker_excerpts.get(a.tracker_id, [])
            if excerpts:
                lines.append("  Recent negative mentions:")
                for ex in excerpts:
                    lines.append(f"    • {ex}")
            seen_trackers.add(a.tracker_id)

    context = "\n".join(lines)

    return await gemma_chat(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a brand intelligence analyst. You receive concurrent alert data from "
                    "multiple brand trackers and must identify the cross-channel pattern. "
                    "Be specific — name the actual issue, not just 'negative sentiment'. "
                    "Use this exact format:\n"
                    "PATTERN: [one sentence describing what's happening across trackers]\n"
                    "CAUSE: [one sentence on the likely root cause or triggering event]\n"
                    "ACTION: [one concrete next step for the comms team]"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Concurrent alerts in the last 4 hours:\n\n{context}\n\n"
                    "Analyze the cross-channel pattern."
                ),
            },
        ],
        max_tokens=1024,  # thinking tokens count against budget
        temperature=0.3,
    )


def _local_insight(alerts: list, trackers: dict) -> str:
    names = [t.name if (t := trackers.get(a.tracker_id)) else str(a.tracker_id) for a in alerts]
    alert_types = list({a.alert_type for a in alerts})
    return (
        f"Concurrent alerts detected across {', '.join(set(names))}. "
        f"Alert types: {', '.join(alert_types)}. "
        "Review these trackers together as they may share a common cause."
    )
