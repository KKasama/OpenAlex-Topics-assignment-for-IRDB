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

Output modes:

* **Full (default)** — Japanese records are enriched with seven fields
  (``topic_id``, ``topic_name``, ``field``, ``subfield``, ``domain``,
  ``confidence``, ``method``); non-Japanese records pass through unchanged.

* **Minimal (``--minimal``)** — only five fields are emitted per processed
  record: ``work_id``, ``topic_id``, ``topic_name``, ``confidence``,
  ``method``. Non-Japanese (skipped) records are omitted from the output.
  Designed for ingesting Topic assignments back into IRDB at scale.

JSONL input/output is streamed line-by-line, so multi-million-record
files are processed without loading everything into memory.

Examples
--------
    # Single paper (inline JSON)
    echo '{"title":"機械学習によるタンパク質構造予測","abstract":"","ndc_codes":["464"]}' \
      | python scripts/assign_topics.py --index-dir ./index

    # Batch from file
    python scripts/assign_topics.py --index-dir ./index --input records.jsonl --output results.jsonl

    # Minimal output for IRDB ingestion (5 columns only)
    python scripts/assign_topics.py --index-dir ./index \
      --input works.jsonl --output topics.jsonl --minimal

    # Process every record regardless of language
    python scripts/assign_topics.py --index-dir ./index --input records.jsonl \
      --output results.jsonl --no-japanese-only
"""

import argparse
import io
import json
import sys
import time
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

MINIMAL_FIELDS = ("work_id", "topic_id", "topic_name", "confidence", "method")
PROGRESS_EVERY = 1000


def _iter_jsonl_lines(path: str | None):
    """Yield (line_number, record_dict) from a JSONL/JSON source.

    Streams files line by line. For stdin (no ``path``) or a JSON-array file,
    falls back to loading everything once.
    """
    if path is None:
        text = sys.stdin.read()
        for i, rec in enumerate(jsonl_text_to_records(text), 1):
            yield i, rec
        return

    p = Path(path)
    # Sniff first non-whitespace char to detect JSON-array files.
    with p.open("r", encoding="utf-8") as f:
        head = ""
        while True:
            ch = f.read(1)
            if not ch:
                break
            if not ch.isspace():
                head = ch
                break

    if head == "[":
        for i, rec in enumerate(jsonl_text_to_records(p.read_text()), 1):
            yield i, rec
        return

    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield i, json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  [warn] line {i}: skipping invalid JSON ({e})", file=sys.stderr)


def _work_id(record: dict) -> str:
    for key in ("id", "work_id", "openalex_id", "url"):
        v = record.get(key)
        if v:
            return str(v)
    return ""


def _minimal_row(record: dict, result) -> dict:
    return {
        "work_id": _work_id(record),
        "topic_id": result.topic_id,
        "topic_name": result.topic_name,
        "confidence": round(result.confidence, 4),
        "method": result.method,
    }


def _full_row(record: dict, result) -> dict:
    return {
        **record,
        "topic_id": result.topic_id,
        "topic_name": result.topic_name,
        "field": result.field,
        "subfield": result.subfield,
        "domain": result.domain,
        "confidence": round(result.confidence, 4),
        "method": result.method,
    }


def _process_jsonl(args, matcher) -> None:
    out_stream: io.IOBase
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        out_stream = open(args.output, "w", encoding="utf-8")
    else:
        out_stream = sys.stdout

    written = 0
    skipped = 0
    processed = 0
    start = time.time()
    try:
        for _, record in _iter_jsonl_lines(args.input):
            processed += 1
            result = matcher.match(
                title=record.get("title", ""),
                abstract=record.get("abstract", ""),
                ndc_codes=record.get("ndc_codes"),
                language=record.get("language"),
                japanese_only=args.japanese_only,
            )
            if result.method == "skipped":
                skipped += 1
                if not args.minimal:
                    out_stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                    written += 1
                continue
            row = _minimal_row(record, result) if args.minimal else _full_row(record, result)
            out_stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1

            if processed % PROGRESS_EVERY == 0 and args.output:
                elapsed = time.time() - start
                rate = processed / elapsed if elapsed else 0.0
                print(
                    f"  processed {processed:,} records "
                    f"({rate:,.1f}/s, {elapsed/60:.1f} min elapsed)",
                    file=sys.stderr,
                )
    finally:
        if args.output:
            out_stream.close()

    if args.output:
        elapsed = time.time() - start
        mode = "minimal" if args.minimal else "full"
        reassigned = processed - skipped
        print(
            f"Wrote {written:,} lines to {args.output} "
            f"({mode}; reassigned {reassigned:,}, skipped {skipped:,} non-Japanese) "
            f"in {elapsed/60:.1f} min",
            file=sys.stderr,
        )
    elif args.japanese_only and skipped:
        print(f"# skipped {skipped:,} non-Japanese record(s)", file=sys.stderr)


def _process_csv(args, matcher) -> None:
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

    out_path = args.output or args.input.rsplit(".", 1)[0] + "-topics.csv"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    skipped = 0

    if args.minimal:
        # Brand-new CSV with the 5 minimal columns, skipping non-JA records.
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            rows: list[dict] = []
            for original, result in zip(original_rows, results):
                if result.method == "skipped":
                    skipped += 1
                    continue
                rows.append({
                    "work_id": _work_id(original),
                    "topic_id": result.topic_id,
                    "topic_name": result.topic_name,
                    "confidence": round(result.confidence, 4),
                    "method": result.method,
                })
            for chunk in write_csv_rows(list(MINIMAL_FIELDS), rows):
                f.write(chunk)
        print(
            f"Wrote {len(rows):,} rows to {out_path} "
            f"(minimal; skipped {skipped:,} non-Japanese)",
            file=sys.stderr,
        )
        return

    merged: list[dict] = []
    for original, result in zip(original_rows, results):
        is_skipped = result.method == "skipped"
        if is_skipped:
            skipped += 1
        merged.append(enrich_row(original, result, skipped=is_skipped))
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        for chunk in write_csv_rows(fieldnames, merged):
            f.write(chunk)
    print(
        f"Wrote {len(merged):,} rows to {out_path} "
        f"(full; reassigned {len(merged) - skipped:,}, skipped {skipped:,} non-Japanese)",
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Assign OpenAlex Topics to IRDB records")
    parser.add_argument("--index-dir", default="./index", help="Directory containing the FAISS index")
    parser.add_argument("--input", default=None, help="Input JSONL/JSON/CSV file (default: stdin)")
    parser.add_argument("--output", default=None, help="Output JSONL/CSV file (default: stdout)")
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
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Emit only (work_id, topic_id, topic_name, confidence, method). "
             "Non-Japanese records are omitted from the output.",
    )
    args = parser.parse_args()

    matcher = TopicMatcher.load(
        index_dir=args.index_dir,
        model_type=args.model,
        confidence_threshold=args.threshold,
        top_k=args.top_k,
    )

    if is_csv_filename(args.input) or is_csv_filename(args.output):
        _process_csv(args, matcher)
    else:
        _process_jsonl(args, matcher)


if __name__ == "__main__":
    main()
