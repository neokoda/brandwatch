"""
Topic clustering: HF API embeddings → UMAP → HDBSCAN → c-TF-IDF keywords → LLM label.
BERTopic not used — avoids the sentence-transformers dependency.
See CLAUDE.md for trade-off notes.
"""
import uuid
import logging
from datetime import datetime, timezone
import httpx
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from backend.models.mention import Mention
from backend.models.topic import TopicCluster
from backend.config import settings

logger = logging.getLogger(__name__)

_HF_ROUTER = "https://router.huggingface.co/hf-inference/models"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"   # feature-extraction; all-MiniLM-L6-v2 returns 404 on new router


async def recluster_tracker(db: AsyncSession, tracker_id: uuid.UUID) -> int:
    """Recluster mentions for a tracker. Returns number of clusters created."""
    from backend.models.tracker import Tracker
    tracker_result = await db.execute(select(Tracker).where(Tracker.id == tracker_id))
    tracker = tracker_result.scalar_one_or_none()
    tracker_name = tracker.name if tracker else "Unknown"
    tracker_keywords = tracker.keywords[:5] if tracker and tracker.keywords else []

    result = await db.execute(
        select(Mention.id, Mention.content_text, Mention.sentiment_score)
        .where(Mention.tracker_id == tracker_id, Mention.language_code == "en")
        .order_by(Mention.ingested_at.desc())
        .limit(2000)
    )
    rows = result.all()

    # Filter out very short or mostly non-ASCII texts
    clean_rows = [
        (r[0], r[1], r[2]) for r in rows
        if len(r[1].strip()) >= 30
        and sum(1 for c in r[1] if ord(c) < 128) / max(len(r[1]), 1) >= 0.85
    ]

    if len(clean_rows) < 8:
        logger.info("recluster_tracker %s: only %d clean EN texts, skipping", tracker_id, len(clean_rows))
        return 0

    ids = [r[0] for r in clean_rows]
    texts = [r[1][:512] for r in clean_rows]
    sentiment_scores = [r[2] if r[2] is not None else 0.5 for r in clean_rows]

    embeddings = await _get_embeddings(texts)
    if embeddings is None:
        return 0

    clusters = _cluster(embeddings, texts)
    if not clusters:
        return 0

    # Remove old clusters for this tracker before writing new ones
    await db.execute(
        update(Mention)
        .where(Mention.tracker_id == tracker_id)
        .values(topic_cluster_id=None)
    )
    await db.execute(delete(TopicCluster).where(TopicCluster.tracker_id == tracker_id))

    now = datetime.now(timezone.utc)
    created = 0
    for cluster_texts, cluster_indices, keywords in clusters:
        label = await _label_cluster(keywords, cluster_texts[:5], tracker_name, tracker_keywords)
        mention_ids = [ids[i] for i in cluster_indices]
        avg_sentiment = round(sum(sentiment_scores[i] for i in cluster_indices) / len(cluster_indices), 3)

        cluster = TopicCluster(
            id=uuid.uuid4(),
            tracker_id=tracker_id,
            label=label,
            label_raw=", ".join(keywords[:5]),
            keywords=keywords[:10],
            mention_count=len(mention_ids),
            sentiment_avg=avg_sentiment,
            period_start=now,
            period_end=now,
        )
        db.add(cluster)
        await db.flush()

        await db.execute(
            update(Mention)
            .where(Mention.id.in_(mention_ids))
            .values(topic_cluster_id=cluster.id)
        )
        created += 1

    await db.commit()
    return created


async def _get_embeddings(texts: list[str]) -> np.ndarray | None:
    """Embed texts in batches of 32 using the HF router endpoint."""
    import asyncio
    url = f"{_HF_ROUTER}/{EMBEDDING_MODEL}"
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}
    batch_size = 32
    all_embeddings = []

    async with httpx.AsyncClient(timeout=90) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for attempt in range(2):
                try:
                    resp = await client.post(url, headers=headers, json={"inputs": batch})
                    if resp.status_code == 503:
                        logger.info("HF model loading, waiting 20s before retry (attempt %d)", attempt + 1)
                        await asyncio.sleep(20)
                        continue
                    resp.raise_for_status()
                    all_embeddings.extend(resp.json())
                    break
                except Exception as exc:
                    logger.warning("HF embedding batch %d error: %s", i // batch_size, exc)
                    if attempt == 1:
                        return None

    return np.array(all_embeddings) if len(all_embeddings) == len(texts) else None


def _cluster(embeddings: np.ndarray, texts: list[str]) -> list[tuple]:
    """Returns list of (cluster_texts, indices, keywords)."""
    n = len(embeddings)
    # Scale min_cluster_size to data size: at least 3, at most 10
    min_cluster_size = max(3, min(10, n // 15))

    try:
        from umap import UMAP
        import hdbscan

        n_components = min(5, max(2, n - 2))
        n_neighbors = min(15, max(2, n - 2))
        reduced = UMAP(n_components=n_components, n_neighbors=n_neighbors, min_dist=0.0, metric="cosine", random_state=42).fit_transform(embeddings)
        labels = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean").fit_predict(reduced)
        logger.info("HDBSCAN: %d texts → %d clusters (noise: %d)", n, len(set(labels)) - (1 if -1 in labels else 0), sum(1 for l in labels if l == -1))
    except Exception as exc:
        logger.warning("Clustering error: %s", exc)
        return []

    clusters: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue
        clusters.setdefault(label, []).append(idx)

    result = []
    for _, indices in clusters.items():
        cluster_texts = [texts[i] for i in indices]
        keywords = _ctfidf_keywords(cluster_texts, texts)
        result.append((cluster_texts, indices, keywords))

    return result


_NOISE_PATTERN = __import__("re").compile(r"^[\d\s\W]+$")  # pure numbers/punctuation

def _ctfidf_keywords(cluster_texts: list[str], all_texts: list[str]) -> list[str]:
    """c-TF-IDF: words overrepresented in the cluster vs the whole corpus."""
    try:
        vec = CountVectorizer(max_features=5000, stop_words="english", ngram_range=(1, 2)).fit(all_texts)
        cluster_mat = vec.transform(cluster_texts).sum(axis=0)
        all_mat = vec.transform(all_texts).sum(axis=0)
        cluster_freq = np.asarray(cluster_mat).flatten()
        all_freq = np.asarray(all_mat).flatten()
        with np.errstate(divide="ignore", invalid="ignore"):
            scores = np.where(all_freq > 0, cluster_freq / all_freq, 0)
        top_indices = scores.argsort()[::-1][:20]
        terms = vec.get_feature_names_out()
        keywords = []
        for i in top_indices:
            if scores[i] <= 0:
                continue
            term = terms[i]
            # Drop pure numbers, single chars, or HTML artifacts
            if len(term) < 3 or _NOISE_PATTERN.match(term) or "href" in term or "http" in term:
                continue
            keywords.append(term)
            if len(keywords) == 10:
                break
        return keywords
    except Exception:
        return []


async def _label_cluster(
    keywords: list[str],
    examples: list[str],
    tracker_name: str = "",
    tracker_keywords: list[str] = [],
) -> str:
    """Generate a specific topic label via Gemma 4, falling back to a keyword heuristic."""
    if not keywords:
        return "Unlabeled"

    from backend.services.gemini import gemma_chat

    keyword_str = ", ".join(keywords[:10])
    examples_str = "\n".join(f"- {e[:250]}" for e in examples[:5])
    brand_ctx = f"Brand being tracked: {tracker_name}"
    if tracker_keywords:
        brand_ctx += f" (monitored keywords: {', '.join(tracker_keywords)})"

    label = await gemma_chat(
        messages=[
            {
                "role": "system",
                "content": (
                    f"You label clusters of brand mentions. {brand_ctx}. "
                    "Labels must be specific to the actual issue — NOT generic. "
                    "Bad: 'Customer Issues', 'Brand Problems', 'Negative Feedback'. "
                    "Good: 'Drive-Thru Wait Times', 'App Payment Failures', 'Price Increase Complaints'. "
                    "Reply with only the label, 3-5 words, no punctuation."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Keywords from this cluster: {keyword_str}\n\n"
                    f"Sample mentions:\n{examples_str}\n\n"
                    "Label:"
                ),
            },
        ],
        max_tokens=1024,  # thinking tokens count against budget; label itself is short
        temperature=0.2,
    )
    if label:
        # Strip any leading "Label:" or quotes Gemma might add
        cleaned = label.split("\n")[0].strip().strip('"').strip("'")
        if cleaned.lower().startswith("label:"):
            cleaned = cleaned[6:].strip()
        return cleaned[:80] if cleaned else _keyword_fallback(keywords)

    return _keyword_fallback(keywords)


def _keyword_fallback(keywords: list[str]) -> str:
    bigrams = [k for k in keywords if " " in k]
    unigrams = [k for k in keywords if " " not in k and len(k) > 3]
    parts: list[str] = []
    if bigrams:
        parts.append(bigrams[0])
    if len(bigrams) >= 2:
        parts.append(bigrams[1])
    elif unigrams:
        parts.append(unigrams[0])
    if not parts:
        parts = keywords[:2]
    return " & ".join(p.title() for p in parts[:2])
