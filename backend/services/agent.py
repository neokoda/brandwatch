import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.account import Account
from backend.models.alert import Alert
from backend.models.mention import Mention

logger = logging.getLogger(__name__)


async def notify_agent(db: AsyncSession, alert: Alert) -> str | None:
    """POST alert to the account's configured agent webhook. Returns draft response text."""
    result = await db.execute(select(Account).where(Account.id == alert.account_id))
    account = result.scalar_one_or_none()
    if not account or not account.agent_webhook_url:
        return None

    # Gather top 5 negative mentions for context
    mentions_result = await db.execute(
        select(Mention)
        .where(Mention.tracker_id == alert.tracker_id)
        .where(Mention.sentiment_label == "negative")
        .order_by(Mention.ingested_at.desc())
        .limit(5)
    )
    mentions = mentions_result.scalars().all()
    excerpts = [m.content_excerpt or m.content_text[:200] for m in mentions]

    system_prompt = (
        "You are a brand reputation analyst. Analyze the alert and draft a concise "
        "professional response strategy for the communications team."
    )
    user_message = (
        f"Alert: {alert.title}\n"
        f"Severity: {alert.severity}\n"
        f"Details: {alert.description}\n\n"
        f"Top negative mentions:\n"
        + "\n".join(f"- {e}" for e in excerpts)
    )

    payload = {
        "model": "hermes",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 512,
    }

    headers = {"Content-Type": "application/json"}
    if account.agent_api_token:
        headers["Authorization"] = f"Bearer {account.agent_api_token}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(account.agent_webhook_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            draft = data["choices"][0]["message"]["content"]
            return draft
    except Exception as exc:
        logger.warning("Agent webhook error for account %s: %s", account.id, exc)
        return None
