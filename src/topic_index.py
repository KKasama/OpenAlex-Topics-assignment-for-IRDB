"""
FAISS-backed index for OpenAlex Topics.

Build once with build_and_save(), then load with load() for fast querying.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

# FAISS uses OpenMP for parallel search. On macOS, that OpenMP runtime
# (libomp / Accelerate) can conflict with the OpenMP/BLAS pulled in by
# PyTorch's MPS backend, causing segfaults the moment FAISS runs after
# an MPS encode. Pinning FAISS to a single thread avoids the conflict
# and is plenty fast for our index size (~4.5k flat vectors).
faiss.omp_set_num_threads(1)

from .openalex_client import fetch_all_topics, topic_text
from .embeddings import EmbeddingModel


@dataclass
class TopicMatch:
    topic_id: str
    display_name: str
    field: str
    subfield: str
    domain: str
    score: float  # cosine similarity [0, 1]


class TopicIndex:
    def __init__(self, topics: list[dict], embeddings: np.ndarray) -> None:
        self.topics = topics
        self._index = faiss.IndexFlatIP(embeddings.shape[1])  # Inner Product == cosine on L2-norm vectors
        self._index.add(embeddings.astype(np.float32))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, dir_path: str | Path) -> None:
        d = Path(dir_path)
        d.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(d / "topics.faiss"))
        import json
        (d / "topics_meta.json").write_text(json.dumps(self.topics, ensure_ascii=False))

    @classmethod
    def load(cls, dir_path: str | Path) -> "TopicIndex":
        d = Path(dir_path)
        import json
        topics = json.loads((d / "topics_meta.json").read_text())
        index = faiss.read_index(str(d / "topics.faiss"))
        obj = cls.__new__(cls)
        obj.topics = topics
        obj._index = index
        return obj

    # ------------------------------------------------------------------
    # Build helpers
    # ------------------------------------------------------------------

    @classmethod
    def build(
        cls,
        model: EmbeddingModel,
        cache_path: str | Path,
        mailto: str = "",
    ) -> "TopicIndex":
        topics = fetch_all_topics(cache_path, mailto=mailto)
        texts = [topic_text(t) for t in topics]
        embeddings = model.encode(texts, is_query=False, show_progress=True)
        return cls(topics, embeddings)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(self, query_vec: np.ndarray, top_k: int = 5) -> list[TopicMatch]:
        return self.query_batch(query_vec, top_k=top_k)[0]

    def query_batch(self, query_matrix: np.ndarray, top_k: int = 5) -> list[list[TopicMatch]]:
        """Run a batched FAISS search and return per-query candidates."""
        q = query_matrix.astype(np.float32)
        if q.ndim == 1:
            q = q.reshape(1, -1)
        scores, indices = self._index.search(q, top_k)
        out: list[list[TopicMatch]] = []
        for row_scores, row_indices in zip(scores, indices):
            matches: list[TopicMatch] = []
            for score, idx in zip(row_scores, row_indices):
                t = self.topics[idx]
                matches.append(
                    TopicMatch(
                        topic_id=t.get("id", ""),
                        display_name=t.get("display_name", ""),
                        field=_safe_name(t, "field"),
                        subfield=_safe_name(t, "subfield"),
                        domain=_safe_name(t, "domain"),
                        score=float(score),
                    )
                )
            out.append(matches)
        return out


def _safe_name(topic: dict, key: str) -> str:
    v = topic.get(key)
    if isinstance(v, dict):
        return v.get("display_name", "")
    return v or ""
