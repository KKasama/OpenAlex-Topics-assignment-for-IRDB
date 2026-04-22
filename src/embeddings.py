"""
Embedding model wrapper supporting multilingual-e5-large and SPECTER2.

multilingual-e5 is preferred for Japanese text.
SPECTER2 is preferred when citation-aware academic embeddings are needed.
"""

from __future__ import annotations

from enum import Enum
from typing import Union

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


class ModelType(str, Enum):
    MULTILINGUAL_E5 = "intfloat/multilingual-e5-large"
    SPECTER2 = "allenai/specter2_base"


def _average_pool(last_hidden_state: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    mask_expanded = attention_mask.unsqueeze(-1).float()
    return (last_hidden_state * mask_expanded).sum(1) / mask_expanded.sum(1).clamp(min=1e-9)


class EmbeddingModel:
    def __init__(
        self,
        model_type: Union[ModelType, str] = ModelType.MULTILINGUAL_E5,
        device: str | None = None,
        batch_size: int = 32,
    ) -> None:
        self.model_type = ModelType(model_type) if isinstance(model_type, str) else model_type
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.batch_size = batch_size

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_type.value)
        self.model = AutoModel.from_pretrained(self.model_type.value).to(self.device)
        self.model.eval()

    def _prefix(self, is_query: bool) -> str:
        """multilingual-e5 requires task-specific prefixes."""
        if self.model_type == ModelType.MULTILINGUAL_E5:
            return "query: " if is_query else "passage: "
        return ""

    def encode(
        self,
        texts: list[str],
        is_query: bool = False,
        show_progress: bool = False,
    ) -> np.ndarray:
        prefix = self._prefix(is_query)
        prefixed = [prefix + t for t in texts]

        all_embeddings: list[np.ndarray] = []
        iterator = range(0, len(prefixed), self.batch_size)

        if show_progress:
            from tqdm import tqdm
            iterator = tqdm(iterator, desc="Encoding", total=(len(prefixed) + self.batch_size - 1) // self.batch_size)

        with torch.no_grad():
            for start in iterator:
                batch = prefixed[start : start + self.batch_size]
                encoded = self.tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                ).to(self.device)
                outputs = self.model(**encoded)
                embeddings = _average_pool(outputs.last_hidden_state, encoded["attention_mask"])
                # L2 normalise for cosine similarity via dot product
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
                all_embeddings.append(embeddings.cpu().numpy())

        return np.vstack(all_embeddings)

    def encode_paper(self, title: str, abstract: str = "") -> np.ndarray:
        """Encode a single paper as a query vector."""
        text = title if not abstract else f"{title} [SEP] {abstract}"
        return self.encode([text], is_query=True)[0]
