#!/usr/bin/env python3
"""
Fetch works from an OpenAlex source and stream them as JSONL,
ready to feed into ``assign_topics.py``.

The IRDB source id is ``S7407056385`` (Institutional Repositories DataBase).
By default this script fetches Japanese-language works (~2.5M as of 2026-05).

Examples
--------
    # Fetch all Japanese papers from IRDB → works.jsonl
    python scripts/fetch_openalex_works.py \
        --source-id S7407056385 \
        --language ja \
        --mailto your@email.example \
        --output works.jsonl

    # Smoke-test with the first 1,000 records only
    python scripts/fetch_openalex_works.py \
        --mailto your@email.example \
        --output works-sample.jsonl \
        --limit 1000

    # Resume an interrupted run
    python scripts/fetch_openalex_works.py \
        --mailto your@email.example \
        --output works.jsonl \
        --resume-cursor "IlsxNTk5OTk5OTk5LCAnaHR0cHM..."

Output: one JSON object per line with the fields the matcher needs:
    {"id": "...", "title": "...", "abstract": "...",
     "language": "ja", "doi": "...", "publication_year": 2024}
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OPENALEX_BASE = "https://api.openalex.org/works"
SELECT_FIELDS = (
    "id,display_name,abstract_inverted_index,language,doi,publication_year"
)
DEFAULT_SOURCE = "S7407056385"  # IRDB
PROGRESS_EVERY = 1000


def reconstruct_abstract(inv_index: dict | None) -> str:
    """Re-assemble the abstract from OpenAlex's inverted index."""
    if not inv_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indices in inv_index.items():
        for idx in indices:
            positions.append((idx, word))
    positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in positions)


def _request_json(url: str, mailto: str, max_retries: int = 5) -> dict:
    """GET with simple exponential-backoff retry."""
    headers = {"User-Agent": f"irdb-topic-matcher (mailto:{mailto})"}
    req = urllib.request.Request(url, headers=headers)
    delay = 1.0
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.load(resp)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            last_err = e
            print(
                f"  [retry {attempt + 1}/{max_retries}] {e!r} — sleeping {delay:.1f}s",
                file=sys.stderr,
            )
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
    raise RuntimeError(f"Failed after {max_retries} retries: {last_err}")


def fetch_works(
    source_id: str,
    language: str | None,
    mailto: str,
    per_page: int = 200,
    limit: int | None = None,
    start_cursor: str = "*",
    cursor_log: Path | None = None,
):
    """Yield works one at a time using OpenAlex cursor pagination."""
    filters = [f"locations.source.id:{source_id}"]
    if language:
        filters.append(f"language:{language}")

    cursor: str | None = start_cursor
    fetched = 0
    total: int | None = None

    while cursor:
        params = {
            "filter": ",".join(filters),
            "per-page": str(per_page),
            "cursor": cursor,
            "select": SELECT_FIELDS,
            "mailto": mailto,
        }
        url = f"{OPENALEX_BASE}?{urllib.parse.urlencode(params)}"
        data = _request_json(url, mailto)

        meta = data.get("meta", {})
        if total is None:
            total = meta.get("count")
            print(
                f"OpenAlex reports {total:,} matching works."
                if isinstance(total, int)
                else "OpenAlex did not return a count.",
                file=sys.stderr,
            )

        results = data.get("results", [])
        if not results:
            break

        for work in results:
            yield {
                "id": work.get("id", ""),
                "title": work.get("display_name") or "",
                "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
                "language": work.get("language"),
                "doi": work.get("doi"),
                "publication_year": work.get("publication_year"),
            }
            fetched += 1
            if limit and fetched >= limit:
                return

        next_cursor = meta.get("next_cursor")
        if cursor_log is not None and next_cursor:
            try:
                cursor_log.write_text(next_cursor)
            except OSError:
                pass
        cursor = next_cursor


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stream OpenAlex works as JSONL for assign_topics.py"
    )
    parser.add_argument("--source-id", default=DEFAULT_SOURCE,
                        help=f"OpenAlex source id (default: {DEFAULT_SOURCE} = IRDB)")
    parser.add_argument("--language", default="ja",
                        help='ISO language filter (default: "ja"; pass "" to disable)')
    parser.add_argument("--mailto", required=True,
                        help="Contact email — required by OpenAlex polite pool")
    parser.add_argument("--output", required=True,
                        help="Output JSONL file path")
    parser.add_argument("--limit", type=int, default=None,
                        help="Stop after N records (useful for smoke tests)")
    parser.add_argument("--per-page", type=int, default=200,
                        help="Page size for the API (max 200)")
    parser.add_argument("--resume-cursor", default="*",
                        help="Restart from a saved cursor (see --cursor-log)")
    parser.add_argument("--cursor-log", default=None,
                        help="Path to write the latest cursor — useful for resuming")
    args = parser.parse_args()

    language = args.language if args.language else None
    cursor_log = Path(args.cursor_log) if args.cursor_log else None
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(
        f"Fetching source={args.source_id} language={language!r} → {out_path}",
        file=sys.stderr,
    )

    count = 0
    start = time.time()
    with out_path.open("w", encoding="utf-8") as fout:
        for work in fetch_works(
            source_id=args.source_id,
            language=language,
            mailto=args.mailto,
            per_page=args.per_page,
            limit=args.limit,
            start_cursor=args.resume_cursor,
            cursor_log=cursor_log,
        ):
            fout.write(json.dumps(work, ensure_ascii=False) + "\n")
            count += 1
            if count % PROGRESS_EVERY == 0:
                elapsed = time.time() - start
                rate = count / elapsed if elapsed else 0.0
                print(
                    f"  fetched {count:,} works "
                    f"({rate:,.0f} works/s, {elapsed/60:.1f} min elapsed)",
                    file=sys.stderr,
                )

    elapsed = time.time() - start
    print(
        f"Done: wrote {count:,} works to {out_path} in {elapsed/60:.1f} min",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
