import uuid
import statistics
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.snapshot import SentimentSnapshot
from backend.models.mention import Mention
from backend.models.tracker import Tracker
from backend.config import settings

HIGH_ENGAGEMENT_THRESHOLD = 1.5  # log(1 + likes + 2*shares + 0.5*comments) ≈ 3.5 weighted units (demo)


async def check_anomalies(db: AsyncSession, tracker_id: uuid.UUID, account_id: uuid.UUID) -> list[dict]:
    """Return list of alert dicts to create after an ingestion batch."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=7)

    result = await db.execute(
        select(SentimentSnapshot)
        .where(SentimentSnapshot.tracker_id == tracker_id)
        .where(SentimentSnapshot.hour_bucket >= window_start)
        .order_by(SentimentSnapshot.hour_bucket)
    )
    snaps = result.scalars().all()

    if len(snaps) < 3:
        return []

    current_hour = now.replace(minute=0, second=0, microsecond=0)
    current_list = [s for s in snaps if s.hour_bucket >= current_hour - timedelta(hours=1)]
    if not current_list:
        return []
    current = current_list[-1]

    historical = [s for s in snaps if s.hour_bucket < current_hour - timedelta(hours=1)]
    if len(historical) < 2:
        return []

    alerts = []

    # --- Negativity surge ---
    neg_shares = [s.negative_count / s.mention_count if s.mention_count else 0 for s in historical]
    if len(neg_shares) >= 2:
        mean_neg = statistics.mean(neg_shares)
        std_neg = statistics.stdev(neg_shares)
        current_neg_share = current.negative_count / current.mention_count if current.mention_count else 0
        threshold = settings.DEFAULT_ALERT_NEGATIVITY_SURGE_Z
        if std_neg > 0:
            z_neg = (current_neg_share - mean_neg) / std_neg
            if z_neg > threshold and current_neg_share > 0.40:
                alerts.append({
                    "tracker_id": tracker_id,
                    "account_id": account_id,
                    "alert_type": "negativity_surge",
                    "severity": "critical" if z_neg > 4 else "warning",
                    "title": "Negativity Surge Detected",
                    "description": f"Negative share {current_neg_share:.1%} is {z_neg:.1f}σ above baseline ({mean_neg:.1%})",
                    "metric_value": current_neg_share,
                    "metric_baseline": mean_neg,
                    "threshold_used": threshold,
                })

    # --- Volume spike ---
    volumes = [s.mention_count for s in historical]
    if len(volumes) >= 2:
        mean_vol = statistics.mean(volumes)
        std_vol = statistics.stdev(volumes)
        threshold = settings.DEFAULT_ALERT_VOLUME_SPIKE_Z
        if std_vol > 0:
            z_vol = (current.mention_count - mean_vol) / std_vol
            if z_vol > threshold:
                alerts.append({
                    "tracker_id": tracker_id,
                    "account_id": account_id,
                    "alert_type": "volume_spike",
                    "severity": "warning",
                    "title": "Volume Spike Detected",
                    "description": f"Mention volume {current.mention_count} is {z_vol:.1f}σ above baseline ({mean_vol:.0f}/hr)",
                    "metric_value": float(current.mention_count),
                    "metric_baseline": mean_vol,
                    "threshold_used": threshold,
                })

    # --- Crisis risk (compound) ---
    current_neg_share = current.negative_count / current.mention_count if current.mention_count else 0
    baseline_vol = statistics.mean([s.mention_count for s in historical]) if historical else 0
    velocity_ratio = current.mention_count / baseline_vol if baseline_vol > 0 else 0
    if (current_neg_share > settings.DEFAULT_ALERT_CRISIS_NEG_SHARE
            and velocity_ratio > 2.0):
        alerts.append({
            "tracker_id": tracker_id,
            "account_id": account_id,
            "alert_type": "crisis_risk",
            "severity": "critical",
            "title": "Crisis Risk Alert",
            "description": f"High negative share {current_neg_share:.1%}, {velocity_ratio:.1f}× baseline volume",
            "metric_value": current_neg_share,
            "metric_baseline": settings.DEFAULT_ALERT_CRISIS_NEG_SHARE,
            "threshold_used": settings.DEFAULT_ALERT_CRISIS_NEG_SHARE,
        })

    # --- High-engagement mention ---
    # Check recent ingested mentions (last 2 hours) for engagement spikes
    recent_cutoff = now - timedelta(hours=2)
    high_eng_result = await db.execute(
        select(Mention)
        .join(Tracker, Mention.tracker_id == Tracker.id)
        .where(
            Mention.tracker_id == tracker_id,
            Mention.ingested_at >= recent_cutoff,
            Mention.engagement_score >= HIGH_ENGAGEMENT_THRESHOLD,
        )
        .order_by(Mention.engagement_score.desc())
        .limit(5)
    )
    high_eng_mentions = high_eng_result.scalars().all()
    if high_eng_mentions:
        top = high_eng_mentions[0]
        alerts.append({
            "tracker_id": tracker_id,
            "account_id": account_id,
            "alert_type": "high_engagement",
            "severity": "warning",
            "title": "High-Engagement Mention Detected",
            "description": (
                f"{len(high_eng_mentions)} high-engagement mention(s) in the last 2h "
                f"(top score: {top.engagement_score:.1f}, source: {top.source_channel})"
            ),
            "metric_value": top.engagement_score,
            "metric_baseline": HIGH_ENGAGEMENT_THRESHOLD,
            "threshold_used": HIGH_ENGAGEMENT_THRESHOLD,
        })

    return alerts
