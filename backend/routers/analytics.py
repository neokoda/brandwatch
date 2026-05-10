import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.mention import Mention
from backend.models.tracker import Tracker
from backend.models.alert import Alert
from backend.models.snapshot import SentimentSnapshot
from backend.schemas.analytics import KPIs, TrendPoint, GeoPoint, SourceBreakdown, AuthorStat, LanguageBreakdown, EmotionStat, VelocityData

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _account_mention_query(account_id, tracker_id=None):
    q = (
        select(Mention)
        .join(Tracker, Mention.tracker_id == Tracker.id)
        .where(Tracker.account_id == account_id)
    )
    if tracker_id:
        q = q.where(Mention.tracker_id == tracker_id)
    return q


@router.get("/kpis", response_model=KPIs)
async def kpis(
    tracker_id: Optional[uuid.UUID] = None,
    days: int = Query(default=7, ge=1, le=90),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    prev_since = since - timedelta(days=days)

    base_q = _account_mention_query(current_user.account_id, tracker_id).where(Mention.ingested_at >= since)
    prev_q = _account_mention_query(current_user.account_id, tracker_id).where(
        Mention.ingested_at >= prev_since, Mention.ingested_at < since
    )

    # Use sq.c.* to avoid SQLAlchemy adding an implicit cross join with the mentions table
    sq = base_q.subquery()
    result = await db.execute(
        select(
            func.count(sq.c.id).label("total"),
            func.sum(case((sq.c.sentiment_label == "positive", 1), else_=0)).label("pos"),
            func.sum(case((sq.c.sentiment_label == "negative", 1), else_=0)).label("neg"),
            func.sum(case((sq.c.sentiment_label == "neutral", 1), else_=0)).label("neu"),
            func.avg(sq.c.engagement_score).label("avg_eng"),
        ).select_from(sq)
    )
    row = result.one()
    total = row.total or 0
    pos = row.pos or 0
    neg = row.neg or 0
    neu = row.neu or 0

    psq = prev_q.subquery()
    prev_result = await db.execute(
        select(
            func.count(psq.c.id).label("total"),
            func.sum(case((psq.c.sentiment_label == "negative", 1), else_=0)).label("neg"),
        ).select_from(psq)
    )
    prev = prev_result.one()
    prev_total = prev.total or 0
    prev_neg = prev.neg or 0

    alerts_result = await db.execute(
        select(func.count(Alert.id))
        .where(Alert.account_id == current_user.account_id, Alert.is_resolved == False)  # noqa: E712
    )
    active_alerts = alerts_result.scalar_one()

    return KPIs(
        total_mentions=total,
        positive_count=pos,
        negative_count=neg,
        neutral_count=neu,
        positive_share=round(pos / total, 3) if total else 0,
        negative_share=round(neg / total, 3) if total else 0,
        avg_engagement=round(float(row.avg_eng or 0), 2),
        active_alerts=active_alerts,
        mentions_delta_pct=round((total - prev_total) / prev_total * 100, 1) if prev_total else None,
        negative_delta_pct=round((neg / total - prev_neg / prev_total) * 100, 1) if total and prev_total else None,
    )


@router.get("/trends", response_model=List[TrendPoint])
async def trends(
    tracker_id: Optional[uuid.UUID] = None,
    days: int = Query(default=14, ge=1, le=90),
    granularity: str = Query(default="day", pattern="^(hour|day|week)$"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        _account_mention_query(current_user.account_id, tracker_id)
        .where(Mention.ingested_at >= since)
    )
    result = await db.execute(q)
    mentions = result.scalars().all()

    from collections import defaultdict
    buckets: dict[datetime, dict] = defaultdict(lambda: {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "sentiment_sum": 0.0, "engagement_sum": 0.0})

    for m in mentions:
        ts = m.ingested_at
        if granularity == "hour":
            key = ts.replace(minute=0, second=0, microsecond=0)
        elif granularity == "week":
            key = ts.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=ts.weekday())
        else:
            key = ts.replace(hour=0, minute=0, second=0, microsecond=0)

        b = buckets[key]
        b["total"] += 1
        b[m.sentiment_label] = b.get(m.sentiment_label, 0) + 1
        b["sentiment_sum"] += m.sentiment_score
        b["engagement_sum"] += m.engagement_score

    # Fill zero-count buckets so the chart renders as a continuous line
    now_ts = datetime.now(timezone.utc)
    if granularity == "hour":
        cursor = since.replace(minute=0, second=0, microsecond=0)
        step = timedelta(hours=1)
    elif granularity == "week":
        cursor = since.replace(hour=0, minute=0, second=0, microsecond=0)
        step = timedelta(weeks=1)
    else:
        cursor = since.replace(hour=0, minute=0, second=0, microsecond=0)
        step = timedelta(days=1)

    empty = {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "sentiment_sum": 0.0, "engagement_sum": 0.0}
    results = []
    while cursor <= now_ts:
        v = buckets.get(cursor, empty)
        results.append(TrendPoint(
            bucket=cursor,
            total=v["total"],
            positive=v.get("positive", 0),
            negative=v.get("negative", 0),
            neutral=v.get("neutral", 0),
            avg_sentiment=round(v["sentiment_sum"] / v["total"], 3) if v["total"] else 0,
            avg_engagement=round(v["engagement_sum"] / v["total"], 3) if v["total"] else 0,
        ))
        cursor += step
    return results


@router.get("/geographic", response_model=List[GeoPoint])
async def geographic(
    tracker_id: Optional[uuid.UUID] = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = _account_mention_query(current_user.account_id, tracker_id).where(
        Mention.ingested_at >= since, Mention.region_code.isnot(None), Mention.region_code != ""
    )
    result = await db.execute(q)
    mentions = result.scalars().all()

    from collections import defaultdict
    regions: dict[str, dict] = defaultdict(lambda: {"total": 0, "neg": 0, "sentiment_sum": 0.0})
    for m in mentions:
        r = regions[m.region_code]
        r["total"] += 1
        if m.sentiment_label == "negative":
            r["neg"] += 1
        r["sentiment_sum"] += m.sentiment_score

    return [
        GeoPoint(
            region_code=k,
            mention_count=v["total"],
            negative_share=round(v["neg"] / v["total"], 3) if v["total"] else 0,
            avg_sentiment=round(v["sentiment_sum"] / v["total"], 3) if v["total"] else 0,
        )
        for k, v in sorted(regions.items(), key=lambda x: -x[1]["total"])
    ]


@router.get("/sources", response_model=List[SourceBreakdown])
async def sources(
    tracker_id: Optional[uuid.UUID] = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = _account_mention_query(current_user.account_id, tracker_id).where(Mention.ingested_at >= since)
    result = await db.execute(q)
    mentions = result.scalars().all()

    from collections import defaultdict
    srcs: dict[str, dict] = defaultdict(lambda: {"total": 0, "pos": 0, "neg": 0, "eng_sum": 0.0})
    for m in mentions:
        s = srcs[m.source_channel]
        s["total"] += 1
        if m.sentiment_label == "positive":
            s["pos"] += 1
        elif m.sentiment_label == "negative":
            s["neg"] += 1
        s["eng_sum"] += m.engagement_score

    return [
        SourceBreakdown(
            source_channel=k,
            mention_count=v["total"],
            positive_count=v["pos"],
            negative_count=v["neg"],
            avg_engagement=round(v["eng_sum"] / v["total"], 3) if v["total"] else 0,
        )
        for k, v in sorted(srcs.items(), key=lambda x: -x[1]["total"])
    ]


@router.get("/authors", response_model=List[AuthorStat])
async def authors(
    tracker_id: Optional[uuid.UUID] = None,
    days: int = 30,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = _account_mention_query(current_user.account_id, tracker_id).where(
        Mention.ingested_at >= since, Mention.author_name.isnot(None)
    )
    result = await db.execute(q)
    mentions = result.scalars().all()

    from collections import defaultdict, Counter
    authors_map: dict[str, dict] = defaultdict(lambda: {"count": 0, "sent_sum": 0.0, "eng_sum": 0.0, "influencer": False, "channels": []})
    for m in mentions:
        a = authors_map[m.author_name]
        a["count"] += 1
        a["sent_sum"] += m.sentiment_score
        a["eng_sum"] += m.engagement_score
        if m.is_influencer:
            a["influencer"] = True
        a["channels"].append(m.source_channel)

    sorted_authors = sorted(authors_map.items(), key=lambda x: -x[1]["count"])[:limit]
    return [
        AuthorStat(
            author_name=k,
            mention_count=v["count"],
            avg_sentiment=round(v["sent_sum"] / v["count"], 3) if v["count"] else 0,
            is_influencer=v["influencer"],
            total_engagement=round(v["eng_sum"], 2),
            top_channel=Counter(v["channels"]).most_common(1)[0][0] if v["channels"] else "",
        )
        for k, v in sorted_authors
    ]


@router.get("/languages", response_model=List[LanguageBreakdown])
async def languages(
    tracker_id: Optional[uuid.UUID] = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = _account_mention_query(current_user.account_id, tracker_id).where(
        Mention.ingested_at >= since, Mention.language_code.isnot(None)
    )
    result = await db.execute(q)
    mentions = result.scalars().all()

    from collections import defaultdict
    langs: dict[str, dict] = defaultdict(lambda: {"total": 0, "pos": 0, "neg": 0})
    for m in mentions:
        l = langs[m.language_code]
        l["total"] += 1
        if m.sentiment_label == "positive":
            l["pos"] += 1
        elif m.sentiment_label == "negative":
            l["neg"] += 1

    return [
        LanguageBreakdown(
            language_code=k,
            mention_count=v["total"],
            positive_share=round(v["pos"] / v["total"], 3) if v["total"] else 0,
            negative_share=round(v["neg"] / v["total"], 3) if v["total"] else 0,
        )
        for k, v in sorted(langs.items(), key=lambda x: -x[1]["total"])
    ]


@router.get("/emotions", response_model=List[EmotionStat])
async def emotions(
    tracker_id: Optional[uuid.UUID] = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = _account_mention_query(current_user.account_id, tracker_id).where(
        Mention.ingested_at >= since, Mention.emotion_label.isnot(None)
    )
    result = await db.execute(q)
    mentions = result.scalars().all()

    from collections import defaultdict, Counter
    counts: Counter = Counter(m.emotion_label for m in mentions)
    total = sum(counts.values())
    return [
        EmotionStat(emotion_label=k, count=v, share=round(v / total, 3) if total else 0)
        for k, v in counts.most_common()
    ]


@router.get("/calendar")
async def calendar(
    tracker_id: Optional[uuid.UUID] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """52-week volume heatmap. Returns {date: YYYY-MM-DD, total, negative_share}."""
    since = datetime.now(timezone.utc) - timedelta(weeks=52)
    q = _account_mention_query(current_user.account_id, tracker_id).where(Mention.ingested_at >= since)
    result = await db.execute(q)
    mentions = result.scalars().all()

    from collections import defaultdict
    days_map: dict[str, dict] = defaultdict(lambda: {"total": 0, "neg": 0})
    for m in mentions:
        day_key = m.ingested_at.date().isoformat()
        days_map[day_key]["total"] += 1
        if m.sentiment_label == "negative":
            days_map[day_key]["neg"] += 1

    return [
        {"date": k, "total": v["total"], "negative_share": round(v["neg"] / v["total"], 3) if v["total"] else 0}
        for k, v in sorted(days_map.items())
    ]


@router.get("/velocity", response_model=VelocityData)
async def velocity(
    tracker_id: Optional[uuid.UUID] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mention velocity: current hourly rate vs 7-day baseline. Also computes negativity z-score."""
    import statistics
    now = datetime.now(timezone.utc)
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    window_start = now - timedelta(days=7)

    q = _account_mention_query(current_user.account_id, tracker_id).where(Mention.ingested_at >= window_start)
    result = await db.execute(q)
    mentions = result.scalars().all()

    # Bucket by hour
    from collections import defaultdict
    hourly: dict = defaultdict(lambda: {"total": 0, "neg": 0})
    for m in mentions:
        hk = m.ingested_at.replace(minute=0, second=0, microsecond=0)
        hourly[hk]["total"] += 1
        if m.sentiment_label == "negative":
            hourly[hk]["neg"] += 1

    current_bucket = hourly.get(current_hour, {"total": 0, "neg": 0})
    current_rate = float(current_bucket["total"])

    # Generate ALL hours in the window (including zero-mention hours) so the
    # baseline isn't inflated by averaging only "active" hours.
    all_past_hours = []
    h = (window_start + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    while h < current_hour:
        all_past_hours.append(hourly.get(h, {"total": 0, "neg": 0}))
        h += timedelta(hours=1)

    if not all_past_hours:
        return VelocityData(
            current_rate=current_rate, baseline_rate=0, mentions_per_day=0, velocity_ratio=1.0,
            trend="stable", current_negative_share=0, baseline_negative_share=0, negativity_z=0,
        )

    historical_counts = [v["total"] for v in all_past_hours]
    baseline_rate = statistics.mean(historical_counts) if historical_counts else 0
    mentions_per_day = round(baseline_rate * 24, 1)

    last_24h_cutoff = (now - timedelta(hours=24)).replace(minute=0, second=0, microsecond=0)
    last_24h_mentions = sum(v["total"] for h, v in hourly.items() if h >= last_24h_cutoff)

    ratio = current_rate / baseline_rate if baseline_rate > 0 else 1.0
    if ratio > 1.15:
        trend = "up"
    elif ratio < 0.85:
        trend = "down"
    else:
        trend = "stable"

    current_neg_share = (current_bucket["neg"] / current_rate) if current_rate > 0 else 0
    hist_neg_shares = [
        v["neg"] / v["total"] if v["total"] > 0 else 0
        for v in all_past_hours
    ]
    baseline_neg_share = statistics.mean(hist_neg_shares) if hist_neg_shares else 0
    neg_std = statistics.stdev(hist_neg_shares) if len(hist_neg_shares) >= 2 else 0
    negativity_z = (current_neg_share - baseline_neg_share) / neg_std if neg_std > 0 else 0

    return VelocityData(
        current_rate=round(current_rate, 1),
        last_24h_mentions=last_24h_mentions,
        baseline_rate=round(baseline_rate, 1),
        mentions_per_day=mentions_per_day,
        velocity_ratio=round(ratio, 2),
        trend=trend,
        current_negative_share=round(current_neg_share, 3),
        baseline_negative_share=round(baseline_neg_share, 3),
        negativity_z=round(negativity_z, 2),
    )
