"""
Main Topic matching pipeline combining:
  1. Embedding-based similarity (SPECTER2 / multilingual-e5)
  2. NDC rule-based fallback / re-ranking

Usage
-----
    matcher = TopicMatcher.load(index_dir="./index")
    result = matcher.match(title="...", abstract="...", ndc_codes=["510"])
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .embeddings import EmbeddingModel, ModelType
from .language import is_japanese
from .ndc_mapping import NDCMapper, NDCMatch
from .topic_index import TopicIndex, TopicMatch


@dataclass
class AssignmentResult:
    # Primary assignment
    topic_id: str
    topic_name: str
    field: str
    subfield: str
    domain: str
    confidence: float  # cosine similarity [0, 1]
    method: str        # "embedding" | "ndc_fallback" | "ndc_rerank" | "skipped" | "none"

    # Runner-up candidates (embedding top-K)
    candidates: list[TopicMatch] = field(default_factory=list)

    # NDC-based signal (if available)
    ndc_match: NDCMatch | None = None


class TopicMatcher:
    def __init__(
        self,
        index: TopicIndex,
        model: EmbeddingModel,
        ndc_mapper: NDCMapper | None = None,
        confidence_threshold: float = 0.5,
        top_k: int = 5,
    ) -> None:
        self.index = index
        self.model = model
        self.ndc_mapper = ndc_mapper or NDCMapper()
        self.confidence_threshold = confidence_threshold
        self.top_k = top_k

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        index_dir: str | Path,
        model_type: ModelType | str = ModelType.MULTILINGUAL_E5,
        ndc_table: str | Path | None = None,
        confidence_threshold: float = 0.5,
        top_k: int = 5,
    ) -> "TopicMatcher":
        index = TopicIndex.load(index_dir)
        model = EmbeddingModel(model_type)
        ndc_mapper = NDCMapper(ndc_table) if ndc_table else NDCMapper()
        return cls(index, model, ndc_mapper, confidence_threshold, top_k)

    # ------------------------------------------------------------------
    # Core matching
    # ------------------------------------------------------------------

    def match(
        self,
        title: str,
        abstract: str = "",
        ndc_codes: list[str] | None = None,
        language: str | None = None,
        japanese_only: bool = False,
    ) -> AssignmentResult:
        """Match a single paper. Convenience wrapper around :meth:`match_many`."""
        return self.match_many(
            [{
                "title": title,
                "abstract": abstract,
                "ndc_codes": ndc_codes,
                "language": language,
            }],
            japanese_only=japanese_only,
        )[0]

    def _finalize(
        self,
        candidates: list[TopicMatch],
        ndc_match: NDCMatch | None,
    ) -> AssignmentResult:
        """Apply NDC re-rank / fallback rules to ranked candidates."""
        best = candidates[0] if candidates else None
        method = "embedding"
        if best and best.score >= self.confidence_threshold:
            if ndc_match:
                best, method = _rerank_with_ndc(candidates, ndc_match)
        elif ndc_match:
            best = _ndc_as_topic_match(ndc_match)
            method = "ndc_fallback"

        if best is None:
            return _empty_result(candidates, ndc_match)

        return AssignmentResult(
            topic_id=best.topic_id,
            topic_name=best.display_name,
            field=best.field,
            subfield=best.subfield,
            domain=best.domain,
            confidence=best.score,
            method=method,
            candidates=candidates,
            ndc_match=ndc_match,
        )

    def match_many(
        self,
        papers: list[dict],
        japanese_only: bool = False,
    ) -> list[AssignmentResult]:
        """Batched match. All non-skipped papers are encoded in a single
        :meth:`EmbeddingModel.encode` call and queried against FAISS in one
        bulk search — drastically faster on GPU/MPS than per-paper calls.

        papers: list of dicts with keys ``title``, ``abstract`` (opt),
                ``ndc_codes`` (opt), ``language`` (opt).
        """
        n = len(papers)
        out: list[AssignmentResult] = [None] * n  # type: ignore[assignment]

        to_encode_idx: list[int] = []
        texts: list[str] = []
        for i, paper in enumerate(papers):
            title = paper.get("title", "") or ""
            abstract = paper.get("abstract", "") or ""
            language = paper.get("language")
            if japanese_only and not is_japanese(title, abstract, language):
                out[i] = _skipped_result()
                continue
            to_encode_idx.append(i)
            texts.append(title if not abstract else f"{title} [SEP] {abstract}")

        if texts:
            query_matrix = self.model.encode(texts, is_query=True)
            candidates_per_paper = self.index.query_batch(query_matrix, top_k=self.top_k)
            for j, i in enumerate(to_encode_idx):
                paper = papers[i]
                ndc_codes = paper.get("ndc_codes")
                ndc_match = self.ndc_mapper.best_match(ndc_codes) if ndc_codes else None
                out[i] = self._finalize(candidates_per_paper[j], ndc_match)

        return out

    def match_batch(
        self,
        papers: list[dict],
        show_progress: bool = False,
        japanese_only: bool = False,
        chunk_size: int = 256,
    ) -> list[AssignmentResult]:
        """Match a list of papers in chunked batches (memory-bounded).

        papers: list of dicts with keys: title, abstract (opt), ndc_codes (opt),
                language (opt — used for Japanese-only filtering).
        """
        results: list[AssignmentResult] = []
        n_chunks = (len(papers) + chunk_size - 1) // chunk_size
        iterator = range(0, len(papers), chunk_size)
        if show_progress:
            from tqdm import tqdm
            iterator = tqdm(iterator, desc="Matching topics", total=n_chunks)
        for start in iterator:
            chunk = papers[start : start + chunk_size]
            results.extend(self.match_many(chunk, japanese_only=japanese_only))
        return results


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _rerank_with_ndc(
    candidates: list[TopicMatch],
    ndc_match: NDCMatch,
    boost: float = 0.05,
) -> tuple[TopicMatch, str]:
    """
    Slightly boost candidates whose field/subfield matches NDC mapping.
    Returns the best candidate and method label.
    """
    boosted_scores: list[tuple[float, TopicMatch]] = []
    for c in candidates:
        score = c.score
        if c.field == ndc_match.field:
            score += boost
        if c.subfield == ndc_match.subfield:
            score += boost
        boosted_scores.append((score, c))

    boosted_scores.sort(key=lambda x: x[0], reverse=True)
    best_score, best = boosted_scores[0]

    method = "ndc_rerank" if best != candidates[0] else "embedding"
    return best, method


def _ndc_as_topic_match(ndc_match: NDCMatch) -> TopicMatch:
    return TopicMatch(
        topic_id="",
        display_name=ndc_match.subfield,
        field=ndc_match.field,
        subfield=ndc_match.subfield,
        domain=ndc_match.domain,
        score=0.0,
    )


def _empty_result(candidates: list[TopicMatch], ndc_match: NDCMatch | None) -> AssignmentResult:
    return AssignmentResult(
        topic_id="",
        topic_name="Unknown",
        field="",
        subfield="",
        domain="",
        confidence=0.0,
        method="none",
        candidates=candidates,
        ndc_match=ndc_match,
    )


def _skipped_result() -> AssignmentResult:
    """Sentinel result for records skipped under Japanese-only mode."""
    return AssignmentResult(
        topic_id="",
        topic_name="",
        field="",
        subfield="",
        domain="",
        confidence=0.0,
        method="skipped",
    )
