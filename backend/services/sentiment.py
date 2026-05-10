import httpx
import logging
from typing import Optional
from backend.config import settings
from backend.services.language import get_sentiment_model

logger = logging.getLogger(__name__)

HF_BASE = "https://router.huggingface.co/hf-inference/models"
BATCH_SIZE = 32

_LABEL_MAP = {
    # cardiffnlp models
    "positive": "positive",
    "negative": "negative",
    "neutral": "neutral",
    "LABEL_0": "negative",
    "LABEL_1": "neutral",
    "LABEL_2": "positive",
}


async def classify_sentiment_batch(texts: list[str], lang_code: Optional[str] = None) -> list[dict]:
    """Classify a batch of texts. Returns list of {label, score, scores}."""
    if not texts:
        return []

    model = get_sentiment_model(lang_code)
    url = f"{HF_BASE}/{model}"
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}

    results = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    headers=headers,
                    json={"inputs": batch, "parameters": {"top_k": None}},
                )
                resp.raise_for_status()
                raw = resp.json()
        except Exception as exc:
            logger.warning("HF sentiment API error: %s", exc)
            results.extend([_unclassified()] * len(batch))
            continue

        for item in raw:
            if not isinstance(item, list):
                results.append(_unclassified())
                continue
            top = max(item, key=lambda x: x["score"])
            label = _LABEL_MAP.get(top["label"], "neutral")
            score = top["score"]
            scores = {_LABEL_MAP.get(s["label"], s["label"]): s["score"] for s in item}
            results.append({"label": label, "score": score, "scores": scores})

    return results


def _unclassified() -> dict:
    return {"label": "unclassified", "score": 0.0, "scores": {}}


async def classify_emotion(text: str) -> dict | None:
    """Classify emotion for English text. Returns {label, score} or None."""
    model = "j-hartmann/emotion-english-distilroberta-base"
    url = f"{HF_BASE}/{model}"
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json={"inputs": text[:512]})
            resp.raise_for_status()
            raw = resp.json()
    except Exception as exc:
        logger.warning("HF emotion API error: %s", exc)
        return None

    if not raw or not isinstance(raw[0], list):
        return None
    top = max(raw[0], key=lambda x: x["score"])
    return {"label": top["label"], "score": top["score"]}
