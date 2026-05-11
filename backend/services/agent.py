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
from backend.services.gemini import gemma_chat

logger = logging.getLogger(__name__)


async def draft_mention_reply(db: AsyncSession, mention: Mention, account_id: uuid.UUID) -> str | None:
    """Draft a reply to a public mention using Gemma 4."""
    engagement_info = ""
    if mention.engagement_raw:
        parts = [f"{k}: {v}" for k, v in mention.engagement_raw.items() if v]
        if parts:
            engagement_info = f"\nEngagement: {', '.join(parts)}"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a brand communications specialist. Given a public mention about a brand, "
                "draft a concise, professional reply that addresses the author's concern or feedback. "
                "The reply should be empathetic, on-brand, and under 100 words. "
                "Reply with only the draft text — no preamble, no labels."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Platform: {mention.source_channel}\n"
                f"Author: {mention.author_name or 'Unknown'}\n"
                f"Sentiment: {mention.sentiment_label}"
                f"{engagement_info}\n\n"
                f"Mention:\n{mention.content_text[:1000]}\n\n"
                "Draft a reply to this mention."
            ),
        },
    ]

    draft = await gemma_chat(messages, max_tokens=200, temperature=0.7)

    # Also forward to BYOA webhook if configured (for notifications only, response ignored)
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if account and account.agent_webhook_url:
        await _forward_to_webhook(account, messages, draft)

    return draft


async def notify_agent(db: AsyncSession, alert: Alert) -> str | None:
    """Draft an alert response using Gemma 4. Also notifies BYOA webhook if configured."""
    mentions_result = await db.execute(
        select(Mention)
        .where(Mention.tracker_id == alert.tracker_id)
        .where(Mention.sentiment_label == "negative")
        .order_by(Mention.ingested_at.desc())
        .limit(5)
    )
    mentions = mentions_result.scalars().all()
    excerpts = "\n".join(f"- {m.content_excerpt or m.content_text[:200]}" for m in mentions)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a brand reputation analyst. Analyze the alert and draft a concise "
                "professional response strategy for the communications team. "
                "Reply with only the strategy text — no preamble, no labels."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Alert: {alert.title}\n"
                f"Severity: {alert.severity}\n"
                f"Details: {alert.description}\n\n"
                f"Top negative mentions:\n{excerpts}"
            ),
        },
    ]

    draft = await gemma_chat(messages, max_tokens=400, temperature=0.5)

    # Forward to BYOA webhook if configured
    result = await db.execute(select(Account).where(Account.id == alert.account_id))
    account = result.scalar_one_or_none()
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
