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
    MULTILINGUAL_E5 = "intfloat/multilingual-e5-large"          # 560M params, 1024-d
    MULTILINGUAL_E5_BASE = "intfloat/multilingual-e5-base"      # 278M params, 768-d
    MULTILINGUAL_E5_SMALL = "intfloat/multilingual-e5-small"    # 118M params, 384-d
    SPECTER2 = "allenai/specter2_base"


_E5_MODELS = {
    ModelType.MULTILINGUAL_E5,
    ModelType.MULTILINGUAL_E5_BASE,
    ModelType.MULTILINGUAL_E5_SMALL,
}


def _coerce_model_type(value: Union[ModelType, str]) -> Union[ModelType, str]:
    """Accept either a ModelType, a value already in the enum, or any
    Hugging Face model name (passed through verbatim)."""
    if isinstance(value, ModelType):
        return value
    try:
        return ModelType(value)
    except ValueError:
        return value  # arbitrary HF model id — leave as-is


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
        self.model_type = _coerce_model_type(model_type)
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                # Apple-Silicon GPU. Big speed-up over CPU for batched encoding.
                device = "mps"
            else:
                device = "cpu"
        self.device = device
        self.batch_size = batch_size

        model_name = self.model_type.value if isinstance(self.model_type, ModelType) else self.model_type
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device)
        self.model.eval()

    def _prefix(self, is_query: bool) -> str:
        """multilingual-e5 family requires task-specific prefixes."""
        if isinstance(self.model_type, ModelType) and self.model_type in _E5_MODELS:
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
