"""
Gemma 4 26B A4B (MoE) via Google AI Studio's OpenAI-compatible endpoint.
Only ~4B parameters are active per token, making inference ~4x faster than 31B dense.
Used for topic labeling, draft replies, alert responses, and cross-channel insights.
"""
import asyncio
import logging
import re
import httpx
from backend.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
_MODEL = "gemma-4-26b-a4b-it"
_MAX_RETRIES = 2
_RETRY_DELAY = 3.0  # seconds between retries on 500

# Gemma 4 outputs chain-of-thought inside <thought>...</thought> before the answer.
# We suppress thinking via <|no_think|> token, but strip any residual blocks as fallback.
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
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{_BASE}/chat/completions", headers=headers, json=payload)

            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices") or []
                if not choices:
                    logger.warning("Gemma returned no choices (attempt %d)", attempt + 1)
                    return None
                content = choices[0].get("message", {}).get("content")
                if not content:
                    # Gemma occasionally returns a message with null/empty content
                    logger.warning("Gemma returned empty content (attempt %d)", attempt + 1)
                    if attempt < _MAX_RETRIES - 1:
                        await asyncio.sleep(_RETRY_DELAY)
                        continue
                    return None
                # Strip chain-of-thought blocks Gemma 4 always prepends
                answer = _THOUGHT_RE.sub("", content).strip()
                if not answer:
                    logger.warning("Gemma returned only thought block, no answer (attempt %d)", attempt + 1)
                    if attempt < _MAX_RETRIES - 1:
                        await asyncio.sleep(_RETRY_DELAY)
                        continue
                    return None
                return answer

            if resp.status_code == 500 and attempt < _MAX_RETRIES - 1:
                logger.info("Gemma 500, retrying in %.0fs (attempt %d)", _RETRY_DELAY, attempt + 1)
                await asyncio.sleep(_RETRY_DELAY)
                continue

            logger.warning("Gemma API %d: %s", resp.status_code, resp.text[:300])
            return None

        except Exception as exc:
            logger.warning("Gemma API error (attempt %d): %s", attempt + 1, exc)
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RETRY_DELAY)

    return None
