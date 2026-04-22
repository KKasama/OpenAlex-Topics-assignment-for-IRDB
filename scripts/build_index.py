#!/usr/bin/env python3
"""
Build the FAISS topic index from OpenAlex Topics API.

Run once before using assign_topics.py.

    python scripts/build_index.py --index-dir ./index --mailto your@email.com
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embeddings import EmbeddingModel, ModelType
from src.topic_index import TopicIndex


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FAISS topic index from OpenAlex")
    parser.add_argument("--index-dir", default="./index", help="Directory to save the index")
    parser.add_argument("--cache", default="./data/topics_cache.json", help="Path to cache fetched topics")
    parser.add_argument("--model", default=ModelType.MULTILINGUAL_E5.value, help="Embedding model to use")
    parser.add_argument("--mailto", default="", help="Email for OpenAlex API polite pool")
    args = parser.parse_args()

    print(f"Loading model: {args.model}")
    model = EmbeddingModel(model_type=args.model)

    print("Fetching / loading OpenAlex Topics …")
    index = TopicIndex.build(model=model, cache_path=args.cache, mailto=args.mailto)

    print(f"Saving index to {args.index_dir} …")
    index.save(args.index_dir)

    print(f"Done. Indexed {len(index.topics)} topics.")


if __name__ == "__main__":
    main()
