"""
Gemma 4 31B via Google AI Studio's OpenAI-compatible endpoint.
Used for topic labeling, draft replies, alert responses, and cross-channel insights.
"""
import logging
import httpx
from backend.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
_MODEL = "gemma-4-31b-it"


async def gemma_chat(
    messages: list[dict],
    max_tokens: int = 256,
    temperature: float = 0.7,
) -> str | None:
    """
    Call Gemma 4 31B. Returns the assistant reply text, or None on failure.
    messages: standard OpenAI format [{"role": "system"|"user"|"assistant", "content": "..."}]
    """
    if not settings.GOOGLE_AI_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GOOGLE_AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            logger.warning("Gemma API %d: %s", resp.status_code, resp.text[:300])
    except Exception as exc:
        logger.warning("Gemma API error: %s", exc)
    return None
