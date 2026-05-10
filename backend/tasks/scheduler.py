"""APScheduler setup. Registered as a fallback when n8n is not running."""
import asyncio
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _run_all_trackers_gdelt():
    from sqlalchemy import select
    from backend.database import async_session_factory
    from backend.models.tracker import Tracker
    from backend.tasks.gdelt_task import run_gdelt_for_tracker
    async with async_session_factory() as db:
        result = await db.execute(select(Tracker.id).where(Tracker.is_active == True))  # noqa: E712
        tracker_ids = [tid for (tid,) in result.all()]
    for i, tid in enumerate(tracker_ids):
        if i > 0:
            await asyncio.sleep(7)  # GDELT rate limit: 1 req/5s
        await run_gdelt_for_tracker(tid)


async def _run_all_trackers_youtube():
    from sqlalchemy import select
    from backend.database import async_session_factory
    from backend.models.tracker import Tracker
    from backend.tasks.youtube_task import run_youtube_for_tracker
    async with async_session_factory() as db:
        result = await db.execute(select(Tracker.id).where(Tracker.is_active == True))  # noqa: E712
        for (tid,) in result.all():
            await run_youtube_for_tracker(tid)


async def _run_all_trackers_reddit():
    from sqlalchemy import select
    from backend.database import async_session_factory
    from backend.models.tracker import Tracker
    from backend.tasks.reddit_task import run_reddit_for_tracker
    async with async_session_factory() as db:
        result = await db.execute(select(Tracker.id).where(Tracker.is_active == True))  # noqa: E712
        for (tid,) in result.all():
            await run_reddit_for_tracker(tid)


async def _run_all_trackers_rss():
    from sqlalchemy import select
    from backend.database import async_session_factory
    from backend.models.tracker import Tracker
    from backend.tasks.rss_task import run_rss_for_tracker
    async with async_session_factory() as db:
        result = await db.execute(select(Tracker.id).where(Tracker.is_active == True))  # noqa: E712
        for (tid,) in result.all():
            await run_rss_for_tracker(tid)


async def _run_all_trackers_hackernews():
    from sqlalchemy import select
    from backend.database import async_session_factory
    from backend.models.tracker import Tracker
    from backend.tasks.hackernews_task import run_hackernews_for_tracker
    async with async_session_factory() as db:
        result = await db.execute(select(Tracker.id).where(Tracker.is_active == True))  # noqa: E712
        for (tid,) in result.all():
            await run_hackernews_for_tracker(tid)


async def _run_all_trackers_bluesky():
    from sqlalchemy import select
    from backend.database import async_session_factory
    from backend.models.tracker import Tracker
    from backend.tasks.bluesky_task import run_bluesky_for_tracker
    async with async_session_factory() as db:
        result = await db.execute(select(Tracker.id).where(Tracker.is_active == True))  # noqa: E712
        for (tid,) in result.all():
            await run_bluesky_for_tracker(tid)


async def _run_all_trackers_mastodon():
    from sqlalchemy import select
    from backend.database import async_session_factory
    from backend.models.tracker import Tracker
    from backend.tasks.mastodon_task import run_mastodon_for_tracker
    async with async_session_factory() as db:
        result = await db.execute(select(Tracker.id).where(Tracker.is_active == True))  # noqa: E712
        for (tid,) in result.all():
            await run_mastodon_for_tracker(tid)


async def _run_all_trackers_playstore():
    from sqlalchemy import select
    from backend.database import async_session_factory
    from backend.models.tracker import Tracker
    from backend.tasks.playstore_task import run_playstore_for_tracker
    async with async_session_factory() as db:
        result = await db.execute(select(Tracker.id).where(Tracker.is_active == True))  # noqa: E712
        for (tid,) in result.all():
            await run_playstore_for_tracker(tid)


async def _run_all_trackers_appstore():
    from sqlalchemy import select
    from backend.database import async_session_factory
    from backend.models.tracker import Tracker
    from backend.tasks.appstore_task import run_appstore_for_tracker
    async with async_session_factory() as db:
        result = await db.execute(select(Tracker.id).where(Tracker.is_active == True))  # noqa: E712
        for (tid,) in result.all():
            await run_appstore_for_tracker(tid)


def setup_scheduler():
    from backend.tasks.cluster_task import run_recluster_all
    from backend.tasks.insight_task import run_insights_all
    from backend.tasks.digest_task import run_weekly_digest

    now = datetime.now(timezone.utc)
    scheduler.add_job(_run_all_trackers_gdelt, IntervalTrigger(minutes=15), id="gdelt", replace_existing=True, next_run_time=now)
    scheduler.add_job(_run_all_trackers_youtube, IntervalTrigger(minutes=30), id="youtube", replace_existing=True, next_run_time=now)
    scheduler.add_job(_run_all_trackers_rss, IntervalTrigger(minutes=30), id="rss", replace_existing=True, next_run_time=now)
    scheduler.add_job(_run_all_trackers_hackernews, IntervalTrigger(minutes=30), id="hackernews", replace_existing=True, next_run_time=now)
    scheduler.add_job(_run_all_trackers_playstore, IntervalTrigger(hours=6), id="playstore", replace_existing=True, next_run_time=now)
    scheduler.add_job(_run_all_trackers_appstore, IntervalTrigger(hours=6), id="appstore", replace_existing=True, next_run_time=now)
    # reddit/bluesky/mastodon disabled until credentials are configured
    scheduler.add_job(run_recluster_all, IntervalTrigger(hours=6), id="recluster", replace_existing=True)
    scheduler.add_job(run_insights_all, IntervalTrigger(hours=2), id="insights", replace_existing=True)
    scheduler.add_job(run_weekly_digest, CronTrigger(day_of_week="mon", hour=8, minute=0), id="digest", replace_existing=True)

    logger.info("APScheduler configured with 12 jobs")
