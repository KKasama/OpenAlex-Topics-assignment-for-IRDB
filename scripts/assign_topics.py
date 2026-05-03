#!/usr/bin/env python3
"""
Assign OpenAlex Topics to IRDB records.

Input formats (auto-detected by extension):

* **JSONL / JSON** — one object per line (or a JSON array):
    {"title": "...", "abstract": "...", "ndc_codes": ["510", "548"], "language": "ja"}

* **OpenAlex Works CSV** — the flat CSV export from openalex.org. The columns
  ``display_name``, ``abstract`` and ``language`` are mapped automatically;
  the original columns are preserved on output and the new Topic columns
  (``topic_id``, ``topic_name``, ``field``, ``subfield``, ``domain``,
  ``confidence``, ``method``) are appended.

By default only Japanese records are re-assigned (the program is targeted at
fixing Topic mis-assignments for Japanese IRDB records). Non-Japanese records
are written through unchanged. Pass ``--no-japanese-only`` to process every
record regardless of language.

Language detection:
  - Honours an explicit ``language`` field (``ja`` / ``jpn`` / ``eng`` / ...).
  - Otherwise infers from kana / CJK characters in title + abstract.

Output: Japanese records get the following added fields:
    topic_id, topic_name, field, subfield, domain, confidence, method
Non-Japanese records pass through unchanged.

Examples
--------
    # Single paper (inline JSON)
    echo '{"title":"機械学習によるタンパク質構造予測","abstract":"","ndc_codes":["464"]}' \
      | python scripts/assign_topics.py --index-dir ./index

    # Batch from file
    python scripts/assign_topics.py --index-dir ./index --input records.jsonl --output results.jsonl

    # Process every record regardless of language
    python scripts/assign_topics.py --index-dir ./index --input records.jsonl \
      --output results.jsonl --no-japanese-only
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embeddings import ModelType
from src.io_adapters import (
    csv_text_to_records,
    enrich_row,
    is_csv_filename,
    jsonl_text_to_records,
    write_csv_rows,
)
from src.topic_matcher import TopicMatcher


def load_records(path: str | None) -> list[dict]:
    text = Path(path).read_text() if path else sys.stdin.read()
    return jsonl_text_to_records(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Assign OpenAlex Topics to IRDB records")
    parser.add_argument("--index-dir", default="./index", help="Directory containing the FAISS index")
    parser.add_argument("--input", default=None, help="Input JSONL/JSON file (default: stdin)")
    parser.add_argument("--output", default=None, help="Output JSONL file (default: stdout)")
    parser.add_argument("--model", default=ModelType.MULTILINGUAL_E5.value)
    parser.add_argument("--threshold", type=float, default=0.5, help="Confidence threshold for embedding match")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--japanese-only",
        dest="japanese_only",
        action="store_true",
        default=True,
        help="Only re-assign Topics for Japanese records (default).",
    )
    parser.add_argument(
        "--no-japanese-only",
        dest="japanese_only",
        action="store_false",
        help="Process every record regardless of language.",
    )
    args = parser.parse_args()

    matcher = TopicMatcher.load(
        index_dir=args.index_dir,
        model_type=args.model,
        confidence_threshold=args.threshold,
        top_k=args.top_k,
    )

    csv_mode = is_csv_filename(args.input) or is_csv_filename(args.output)
    if csv_mode:
        if not args.input:
            print("CSV mode requires --input", file=sys.stderr)
            sys.exit(2)
        text = Path(args.input).read_text()
        matcher_inputs, original_rows, fieldnames = csv_text_to_records(text)
        results = matcher.match_batch(
            matcher_inputs,
            show_progress=True,
            japanese_only=args.japanese_only,
        )
        skipped = 0
        merged: list[dict] = []
        for original, result in zip(original_rows, results):
            is_skipped = result.method == "skipped"
            if is_skipped:
                skipped += 1
            merged.append(enrich_row(original, result, skipped=is_skipped))

        out_path = args.output or args.input.rsplit(".", 1)[0] + "-topics.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            for chunk in write_csv_rows(fieldnames, merged):
                f.write(chunk)
        print(
            f"Wrote {len(merged)} rows to {out_path} "
            f"(reassigned {len(merged) - skipped}, skipped {skipped} non-Japanese)",
            file=sys.stderr,
        )
        return

    # JSONL / JSON path.
    records = load_records(args.input)
    out_lines = []
    skipped = 0
    results = matcher.match_batch(
        records,
        show_progress=True,
        japanese_only=args.japanese_only,
    )
    for record, result in zip(records, results):
        if result.method == "skipped":
            # Non-Japanese record: pass through unchanged.
            out_lines.append(json.dumps(record, ensure_ascii=False))
            skipped += 1
            continue
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
        print(
            f"Wrote {len(out_lines)} records to {args.output} "
            f"(reassigned {len(out_lines) - skipped}, skipped {skipped} non-Japanese)",
            file=sys.stderr,
        )
    else:
        print(output)
        if args.japanese_only and skipped:
            print(
                f"# skipped {skipped} non-Japanese record(s)",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
