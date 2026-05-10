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
from sqlalchemy import select, update
from backend.models.mention import Mention
from backend.models.topic import TopicCluster
from backend.config import settings

logger = logging.getLogger(__name__)

HF_BASE = "https://api-inference.huggingface.co/models"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


async def recluster_tracker(db: AsyncSession, tracker_id: uuid.UUID) -> int:
    """Recluster mentions for a tracker. Returns number of clusters created."""
    result = await db.execute(
        select(Mention.id, Mention.content_text)
        .where(Mention.tracker_id == tracker_id)
        .order_by(Mention.ingested_at.desc())
        .limit(2000)
    )
    rows = result.all()
    if len(rows) < 10:
        return 0

    ids = [r[0] for r in rows]
    texts = [r[1][:512] for r in rows]

    embeddings = await _get_embeddings(texts)
    if embeddings is None:
        return 0

    clusters = _cluster(embeddings, texts)
    if not clusters:
        return 0

    now = datetime.now(timezone.utc)
    created = 0
    for cluster_texts, cluster_indices, keywords in clusters:
        label = await _label_cluster(keywords, cluster_texts[:3])
        mention_ids = [ids[i] for i in cluster_indices]

        cluster = TopicCluster(
            id=uuid.uuid4(),
            tracker_id=tracker_id,
            label=label,
            label_raw=", ".join(keywords[:5]),
            keywords=keywords[:10],
            mention_count=len(mention_ids),
            sentiment_avg=0.0,
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
    url = f"{HF_BASE}/{EMBEDDING_MODEL}"
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json={"inputs": texts})
            resp.raise_for_status()
            return np.array(resp.json())
    except Exception as exc:
        logger.warning("HF embedding API error: %s", exc)
        return None


def _cluster(embeddings: np.ndarray, texts: list[str]) -> list[tuple]:
    """Returns list of (cluster_texts, indices, keywords)."""
    try:
        from umap import UMAP
        import hdbscan

        reduced = UMAP(n_components=5, n_neighbors=15, min_dist=0.0, metric="cosine").fit_transform(embeddings)
        labels = hdbscan.HDBSCAN(min_cluster_size=5, metric="euclidean").fit_predict(reduced)
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
        top_indices = scores.argsort()[::-1][:10]
        terms = vec.get_feature_names_out()
        return [terms[i] for i in top_indices if scores[i] > 0]
    except Exception:
        return []


async def _label_cluster(keywords: list[str], examples: list[str]) -> str:
    if not keywords:
        return "Unlabeled"
    if not settings.HUGGINGFACE_API_TOKEN:
        return keywords[0].title() if keywords else "Topic"

    model = "mistralai/Mistral-7B-Instruct-v0.3"
    url = f"{HF_BASE}/{model}"
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}
    keyword_str = ", ".join(keywords[:8])
    examples_str = "\n".join(f"- {e[:100]}" for e in examples)
    prompt = (
        f"Keywords: {keyword_str}\n"
        f"Example mentions:\n{examples_str}\n\n"
        "Give this topic a short label (3-5 words). Respond with only the label."
    )
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                url, headers=headers,
                json={"inputs": prompt, "parameters": {"max_new_tokens": 20, "return_full_text": False}},
            )
            resp.raise_for_status()
            text = resp.json()[0]["generated_text"].strip().split("\n")[0]
            return text[:80] or keywords[0].title()
    except Exception:
        return keywords[0].title() if keywords else "Topic"
