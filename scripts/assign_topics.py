#!/usr/bin/env python3
"""
Assign OpenAlex Topics to IRDB records.

Input JSON format (one object per line or a JSON array):
    {"title": "...", "abstract": "...", "ndc_codes": ["510", "548"]}

Output: same records with added fields:
    topic_id, topic_name, field, subfield, domain, confidence, method

Examples
--------
    # Single paper (inline JSON)
    echo '{"title":"機械学習によるタンパク質構造予測","abstract":"","ndc_codes":["464"]}' \
      | python scripts/assign_topics.py --index-dir ./index

    # Batch from file
    python scripts/assign_topics.py --index-dir ./index --input records.jsonl --output results.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embeddings import ModelType
from src.topic_matcher import TopicMatcher


def load_records(path: str | None) -> list[dict]:
    text = Path(path).read_text() if path else sys.stdin.read()
    text = text.strip()
    if text.startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.split('\n') if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Assign OpenAlex Topics to IRDB records")
    parser.add_argument("--index-dir", default="./index", help="Directory containing the FAISS index")
    parser.add_argument("--input", default=None, help="Input JSONL/JSON file (default: stdin)")
    parser.add_argument("--output", default=None, help="Output JSONL file (default: stdout)")
    parser.add_argument("--model", default=ModelType.MULTILINGUAL_E5.value)
    parser.add_argument("--threshold", type=float, default=0.5, help="Confidence threshold for embedding match")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    records = load_records(args.input)
    matcher = TopicMatcher.load(
        index_dir=args.index_dir,
        model_type=args.model,
        confidence_threshold=args.threshold,
        top_k=args.top_k,
    )

    out_lines = []
    results = matcher.match_batch(records, show_progress=True)
    for record, result in zip(records, results):
        enriched = {
            **record,
            "topic_id": result.topic_id,
            "topic_name": result.topic_name,
            "field": result.field,
            "subfield": result.subfield,
            "domain": result.domain,
            "confidence": round(result.confidence, 4),
            "method": result.method,
        }
        out_lines.append(json.dumps(enriched, ensure_ascii=False))

    output = "\n".join(out_lines)
    if args.output:
        Path(args.output).write_text(output)
        print(f"Wrote {len(out_lines)} records to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
