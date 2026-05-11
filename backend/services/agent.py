"""
AI-powered draft generation using Gemma 4 31B via Google AI Studio.
Gemma handles all draft generation directly. If the account has configured a BYOA webhook,
the alert payload is also forwarded there for notifications (Telegram, Slack, etc.).
"""
import uuid
import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.account import Account
from backend.models.alert import Alert
from backend.models.mention import Mention
from backend.models.tracker import Tracker
from backend.services.gemini import gemma_chat

logger = logging.getLogger(__name__)


async def draft_mention_reply(db: AsyncSession, mention: Mention, account_id: uuid.UUID) -> str | None:
    """Draft a reply to a public mention using Gemma 4."""
    # Fetch brand name for context
    account_result = await db.execute(select(Account).where(Account.id == account_id))
    account = account_result.scalar_one_or_none()
    brand_name = account.name if account else "the brand"

    tracker_name = ""
    if mention.tracker_id:
        t_result = await db.execute(select(Tracker).where(Tracker.id == mention.tracker_id))
        t = t_result.scalar_one_or_none()
        tracker_name = f" ({t.name})" if t else ""

    engagement_info = ""
    if mention.engagement_raw:
        parts = [f"{k}: {v}" for k, v in mention.engagement_raw.items() if v]
        if parts:
            engagement_info = f"\nEngagement: {', '.join(parts)}"

    influencer_note = " [INFLUENCER — high reach]" if mention.is_influencer else ""

    messages = [
        {
            "role": "system",
            "content": (
                f"You are a brand communications specialist for {brand_name}{tracker_name}. "
                "Draft a concise, professional public reply to the mention below. "
                "Be empathetic and specific — address the actual issue raised, not a generic response. "
                "Under 100 words. Reply with only the draft text — no preamble, no labels."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Platform: {mention.source_channel}\n"
                f"Author: {mention.author_name or 'Unknown'}{influencer_note}\n"
                f"Sentiment: {mention.sentiment_label}"
                f"{engagement_info}\n\n"
                f"Mention:\n{mention.content_text[:1200]}\n\n"
                "Draft a reply:"
            ),
        },
    ]

    draft = await gemma_chat(messages, max_tokens=200, temperature=0.7)

    if account and account.agent_webhook_url:
        await _forward_to_webhook(account, messages, draft)

    return draft


async def notify_agent(db: AsyncSession, alert: Alert) -> str | None:
    """Draft an alert response strategy using Gemma 4. Notifies BYOA webhook if configured."""
    # Fetch tracker and account for full context
    tracker_name, tracker_keywords = "Unknown tracker", []
    if alert.tracker_id:
        t_result = await db.execute(select(Tracker).where(Tracker.id == alert.tracker_id))
        t = t_result.scalar_one_or_none()
        if t:
            tracker_name = t.name
            tracker_keywords = (t.keywords or [])[:5]

    account_result = await db.execute(select(Account).where(Account.id == alert.account_id))
    account = account_result.scalar_one_or_none()
    brand_name = account.name if account else "the brand"

    mentions_result = await db.execute(
        select(Mention)
        .where(Mention.tracker_id == alert.tracker_id)
        .where(Mention.sentiment_label == "negative")
        .order_by(Mention.ingested_at.desc())
        .limit(5)
    )
    mentions = mentions_result.scalars().all()
    excerpts = "\n".join(
        f"  [{m.source_channel}] {m.author_name or 'Unknown'}: {(m.content_excerpt or m.content_text)[:250]}"
        for m in mentions
    )

    metric_str = ""
    if alert.metric_value is not None and alert.metric_baseline is not None:
        metric_str = f"\nMetric: {alert.metric_value:.2f} (baseline {alert.metric_baseline:.2f})"
    elif alert.metric_value is not None:
        metric_str = f"\nMetric: {alert.metric_value:.2f}"

    kw_str = f"\nTracked keywords: {', '.join(tracker_keywords)}" if tracker_keywords else ""

    messages = [
        {
            "role": "system",
            "content": (
                f"You are a brand reputation analyst for {brand_name}. "
                "Given an alert and supporting mention excerpts, draft a concise response strategy "
                "for the communications team. Be specific: name the issue, the scale, and a concrete "
                "first action. Use this format:\n"
                "SITUATION: [one sentence on what's happening and scale]\n"
                "PRIORITY: [critical/high/medium]\n"
                "RECOMMENDED ACTION: [one or two concrete sentences on what to do next]"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Brand: {brand_name}\n"
                f"Tracker: {tracker_name}{kw_str}\n"
                f"Alert: {alert.title} [{alert.severity}]\n"
                f"Details: {alert.description}{metric_str}\n\n"
                f"Recent negative mentions:\n{excerpts}\n\n"
                "Draft the response strategy:"
            ),
        },
    ]

    draft = await gemma_chat(messages, max_tokens=300, temperature=0.4)

    if account and account.agent_webhook_url:
        await _forward_to_webhook(account, messages, draft)

    return draft


async def _forward_to_webhook(account: Account, messages: list[dict], draft: str | None) -> None:
    """Fire-and-forget: POST to the account's BYOA webhook for notifications (Telegram, Slack, etc.)."""
    payload = {
        "model": "gemma-4-31b-it",
        "messages": messages,
        "draft": draft,
    }
    headers = {"Content-Type": "application/json"}
    if account.agent_api_token:
        headers["Authorization"] = f"Bearer {account.agent_api_token}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(account.agent_webhook_url, json=payload, headers=headers)
    except Exception as exc:
        logger.debug("BYOA webhook notify failed (non-critical): %s", exc)
