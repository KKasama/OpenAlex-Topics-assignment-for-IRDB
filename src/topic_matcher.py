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
    method: str        # "embedding" | "ndc_fallback" | "ndc_rerank"

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
    ) -> AssignmentResult:
        # Step 1: embedding-based retrieval
        query_vec = self.model.encode_paper(title, abstract)
        candidates = self.index.query(query_vec, top_k=self.top_k)

        # Step 2: NDC lookup
        ndc_match: NDCMatch | None = None
        if ndc_codes:
            ndc_match = self.ndc_mapper.best_match(ndc_codes)

        best = candidates[0] if candidates else None

        # Step 3: decide final assignment
        method = "embedding"
        if best and best.score >= self.confidence_threshold:
            # High-confidence embedding hit: optionally re-rank using NDC
            if ndc_match:
                best, method = _rerank_with_ndc(candidates, ndc_match)
        elif ndc_match:
            # Low-confidence embedding → fall back to NDC
            best = _ndc_as_topic_match(ndc_match)
            method = "ndc_fallback"
        # else: keep the best embedding match even below threshold

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

    def match_batch(
        self,
        papers: list[dict],
        show_progress: bool = False,
    ) -> list[AssignmentResult]:
        """
        papers: list of dicts with keys: title, abstract (opt), ndc_codes (opt)
        """
        results = []
        iterator = papers
        if show_progress:
            from tqdm import tqdm
            iterator = tqdm(papers, desc="Matching topics")
        for paper in iterator:
            results.append(
                self.match(
                    title=paper.get("title", ""),
                    abstract=paper.get("abstract", ""),
                    ndc_codes=paper.get("ndc_codes"),
                )
            )
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
