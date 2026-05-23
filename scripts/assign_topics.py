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
CHUNK_SIZE = 256  # records encoded + queried in one batched pass


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


def _ordered_topic_objects(result, top_n: int) -> tuple[dict | None, list[dict]]:
    """Return ``(primary_topic, topics)`` in OpenAlex-aligned shape.

    ``primary_topic`` is the topic chosen by the matcher (which may differ
    from candidates[0] when NDC re-rank fires). ``topics`` is a list of
    up to ``top_n`` items, with the primary moved to position 0 so the
    list mirrors OpenAlex's convention.
    """
    candidates = list(getattr(result, "candidates", []) or [])

    # Fallback when no candidates (e.g. ndc_fallback synthesises a topic).
    if not candidates:
        topic = {
            "id": result.topic_id,
            "display_name": result.topic_name,
            "score": round(result.confidence, 4),
        }
        return (topic if result.topic_id or result.topic_name else None,
                [topic] if result.topic_id or result.topic_name else [])

    # Reorder so the chosen primary (result.topic_id) is first.
    if candidates[0].topic_id != result.topic_id:
        for i, c in enumerate(candidates):
            if c.topic_id == result.topic_id:
                candidates.insert(0, candidates.pop(i))
                break

    topics = [
        {
            "id": c.topic_id,
            "display_name": c.display_name,
            "score": round(c.score, 4),
        }
        for c in candidates[:max(top_n, 1)]
    ]
    return (topics[0] if topics else None, topics)


def _minimal_row_multi(record: dict, result, top_n: int) -> dict:
    """OpenAlex-aligned minimal row: work_id + primary_topic + topics + method."""
    primary, topics = _ordered_topic_objects(result, top_n)
    return {
        "work_id": _work_id(record),
        "primary_topic": primary,
        "topics": topics,
        "method": result.method,
    }


def _full_row_multi(record: dict, result, top_n: int) -> dict:
    """Original record + OpenAlex-aligned ``primary_topic`` / ``topics``."""
    primary, topics = _ordered_topic_objects(result, top_n)
    return {
        **record,
        "primary_topic": primary,
        "topics": topics,
        "field": result.field,
        "subfield": result.subfield,
        "domain": result.domain,
        "method": result.method,
    }


def _flush_chunk(
    chunk: list[dict],
    matcher,
    out_stream,
    *,
    japanese_only: bool,
    minimal: bool,
    multi_topic: bool = False,
    top_n: int = 3,
) -> tuple[int, int]:
    """Match a chunk in one batched pass and write results. Returns (written, skipped)."""
    results = matcher.match_many(chunk, japanese_only=japanese_only)
    written = 0
    skipped = 0
    for record, result in zip(chunk, results):
        if result.method == "skipped":
            skipped += 1
            if not minimal:
                out_stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
            continue
        if multi_topic:
            row = (
                _minimal_row_multi(record, result, top_n)
                if minimal
                else _full_row_multi(record, result, top_n)
            )
        else:
            row = _minimal_row(record, result) if minimal else _full_row(record, result)
        out_stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        written += 1
    return written, skipped


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
    chunk: list[dict] = []
    start = time.time()
    next_log_at = PROGRESS_EVERY  # log every PROGRESS_EVERY processed records
    try:
        for _, record in _iter_jsonl_lines(args.input):
            chunk.append(record)
            processed += 1
            if len(chunk) >= CHUNK_SIZE:
                w, s = _flush_chunk(
                    chunk, matcher, out_stream,
                    japanese_only=args.japanese_only,
                    minimal=args.minimal,
                    multi_topic=args.multi_topic,
                    top_n=args.top_n,
                )
                written += w
                skipped += s
                chunk = []
                if processed >= next_log_at and args.output:
                    elapsed = time.time() - start
                    rate = processed / elapsed if elapsed else 0.0
                    print(
                        f"  processed {processed:,} records "
                        f"({rate:,.1f}/s, {elapsed/60:.1f} min elapsed)",
                        file=sys.stderr,
                        flush=True,
                    )
                    # Bump to next multiple of PROGRESS_EVERY at or above processed.
                    next_log_at = ((processed // PROGRESS_EVERY) + 1) * PROGRESS_EVERY
        # Flush leftover.
        if chunk:
            w, s = _flush_chunk(
                chunk, matcher, out_stream,
                japanese_only=args.japanese_only,
                minimal=args.minimal,
                multi_topic=args.multi_topic,
                top_n=args.top_n,
            )
            written += w
            skipped += s
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
    if args.multi_topic:
        print(
            "--multi-topic is not supported for CSV output yet; use JSONL output "
            "(e.g. --output topics.jsonl) for OpenAlex-aligned schema.",
            file=sys.stderr,
        )
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
    parser.add_argument(
        "--multi-topic",
        action="store_true",
        help="OpenAlex-aligned output with ``primary_topic`` (single) + "
             "``topics`` (array of up to --top-n). When unset, only the best "
             "topic is emitted (flat fields, backward compatible).",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=3,
        help="When --multi-topic is set, number of topics to emit per record "
             "(default 3, matching OpenAlex convention). Capped by --top-k.",
    )
    args = parser.parse_args()

    if args.multi_topic and args.top_n > args.top_k:
        # Need at least top_n candidates retrieved from FAISS.
        args.top_k = args.top_n

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
