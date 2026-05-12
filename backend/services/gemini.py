"""
Gemini 2.0 Flash via Google AI Studio's OpenAI-compatible endpoint.
Fast, low-latency model. Used for topic labeling, draft replies, alert responses,
and cross-channel insights.
"""
import asyncio
import logging
import re
import httpx
from backend.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
_MODEL = "gemini-3.1-flash-lite"
_MAX_RETRIES = 5
_RETRY_BASE_DELAY = 3.0  # base for exponential backoff

# Strip any chain-of-thought blocks (legacy Gemma artefact, harmless for Gemini)
_THOUGHT_RE = re.compile(r"<thought>.*?</thought>\s*", re.DOTALL)


def _merge_system_into_user(messages: list[dict]) -> list[dict]:
    """
    Gemma's chat template has no system turn — prepend any system message
    content to the first user message. Also prepend <|no_think|> to suppress
    the chain-of-thought reasoning pass (saves tokens and latency).
    """
    result = []
    pending_system: list[str] = []
    first_user_seen = False
    for msg in messages:
        if msg.get("role") == "system":
            pending_system.append(msg["content"])
        elif msg.get("role") == "user":
            parts = []
            if not first_user_seen:
                parts.append("<|no_think|>")
                first_user_seen = True
            if pending_system:
                parts.extend(pending_system)
                pending_system = []
            parts.append(msg["content"])
            result.append({"role": "user", "content": "\n\n".join(parts)})
        else:
            result.append(msg)
    return result


async def gemma_chat(
    messages: list[dict],
    max_tokens: int = 256,
    temperature: float = 0.7,
) -> str | None:
    """
    Call Gemma 4 31B. Returns the assistant reply text, or None on failure.
    Retries once on 500 (transient server errors are common on large models).
    messages: standard OpenAI format [{"role": "system"|"user"|"assistant", "content": "..."}]
    """
    if not settings.GOOGLE_AI_API_KEY:
        return None

    # Gemma uses only user/assistant turns — no native system role.
    # Merge any system message into the first user message so the API doesn't 500.
    normalized = _merge_system_into_user(messages)

    payload = {
        "model": _MODEL,
        "messages": normalized,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {settings.GOOGLE_AI_API_KEY}",
        "Content-Type": "application/json",
    }

    for attempt in range(_MAX_RETRIES):
        delay = _RETRY_BASE_DELAY * (2 ** attempt)  # exponential: 3, 6, 12, 24, 48s
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(f"{_BASE}/chat/completions", headers=headers, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices") or []
                if not choices:
                    logger.warning("Gemini returned no choices (attempt %d)", attempt + 1)
                    return None
                content = choices[0].get("message", {}).get("content")
                if not content:
                    logger.warning("Gemini returned empty content (attempt %d)", attempt + 1)
                    if attempt < _MAX_RETRIES - 1:
                        await asyncio.sleep(delay)
                        continue
                    return None
                answer = _THOUGHT_RE.sub("", content).strip()
                if not answer:
                    logger.warning("Gemini returned only thought block (attempt %d)", attempt + 1)
                    if attempt < _MAX_RETRIES - 1:
                        await asyncio.sleep(delay)
                        continue
                    return None
                return answer

            if resp.status_code in (429, 500, 503) and attempt < _MAX_RETRIES - 1:
                logger.info("Gemini %d, retrying in %.0fs (attempt %d)", resp.status_code, delay, attempt + 1)
                await asyncio.sleep(delay)
                continue

            logger.warning("Gemini API %d: %s", resp.status_code, resp.text[:300])
            return None

        except Exception as exc:
            logger.warning("Gemini API error (attempt %d): %s", attempt + 1, exc)
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(delay)

    return None
