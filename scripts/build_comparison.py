#!/usr/bin/env python3
"""
Build a side-by-side comparison between the existing OpenAlex Topic
assignment and the Topic re-assignment produced by this project.

Reads the local ``topics-1k-multi.jsonl``, picks a sample of work IDs,
fetches each Work's existing ``primary_topic`` / ``topics`` from
OpenAlex, and emits a Markdown + CSV table for inclusion in
reports / cover letters.

Usage
-----
    export OPENALEX_API_KEY=...        # optional, Premium tier
    python scripts/build_comparison.py \
        --input  data/topics-1k-multi.jsonl \
        --sample 10 \
        --mailto your@example.org \
        --out-md  docs/comparison-1k.md \
        --out-csv docs/comparison-1k.csv
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OPENALEX_BASE = "https://api.openalex.org/works"


def fetch_work(work_url: str, mailto: str, api_key: str | None) -> dict:
    """Fetch a single Work record. Returns the JSON dict."""
    # work_url ends with "/W..." — extract the bare ID
    work_id = work_url.rstrip("/").split("/")[-1]
    params = {
        "select": "id,display_name,primary_topic,topics",
        "mailto": mailto,
    }
    if api_key:
        params["api_key"] = api_key
    url = f"{OPENALEX_BASE}/{work_id}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": f"irdb-topic-matcher (mailto:{mailto})"}
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except Exception as e:
            print(f"  [retry {attempt + 1}/5] {e!r}", file=sys.stderr)
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {work_url}")


def short(s: str, n: int = 60) -> str:
    return (s[:n] + "…") if s and len(s) > n else (s or "")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="data/topics-1k-multi.jsonl")
    p.add_argument("--sample", type=int, default=10)
    p.add_argument("--mailto", required=True)
    p.add_argument("--out-md", default="docs/comparison-1k.md")
    p.add_argument("--out-csv", default="docs/comparison-1k.csv")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    api_key = os.environ.get("OPENALEX_API_KEY")

    # Load our results.
    with open(args.input) as f:
        ours = [json.loads(line) for line in f]
    print(f"Loaded {len(ours):,} records from {args.input}", file=sys.stderr)

    # Sample.
    rnd = random.Random(args.seed)
    picks = rnd.sample(ours, min(args.sample, len(ours)))
    print(f"Sampling {len(picks)} works for comparison", file=sys.stderr)

    rows: list[dict] = []
    for i, rec in enumerate(picks, 1):
        work_id = rec["work_id"]
        print(f"  [{i}/{len(picks)}] {work_id}", file=sys.stderr)
        try:
            w = fetch_work(work_id, args.mailto, api_key)
        except Exception as e:
            print(f"    skip ({e})", file=sys.stderr)
            continue

        existing_primary = (w.get("primary_topic") or {}).get("display_name", "")
        existing_topics = [(t.get("display_name") or "") for t in (w.get("topics") or [])][:3]
        while len(existing_topics) < 3:
            existing_topics.append("")

        ours_primary = (rec.get("primary_topic") or {}).get("display_name", "")
        ours_topics_list = [t.get("display_name", "") for t in (rec.get("topics") or [])][:3]
        while len(ours_topics_list) < 3:
            ours_topics_list.append("")

        rows.append({
            "work_id": work_id,
            "title": w.get("display_name", ""),
            "existing_primary": existing_primary,
            "existing_topic_2": existing_topics[1],
            "existing_topic_3": existing_topics[2],
            "ours_primary": ours_primary,
            "ours_topic_2": ours_topics_list[1],
            "ours_topic_3": ours_topics_list[2],
            "primary_changed": existing_primary != ours_primary,
        })

    # Write CSV.
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    import csv
    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {args.out_csv}", file=sys.stderr)

    # Write Markdown.
    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    md_lines: list[str] = []
    md_lines.append("# 改善比較表（既存 OpenAlex vs 本手法、1,000 件サンプルから抜粋）")
    md_lines.append("")
    md_lines.append(f"**サンプル件数：** {len(rows)} 件（無作為抽出、seed={args.seed}）")
    md_lines.append("")
    n_changed = sum(1 for r in rows if r["primary_changed"])
    md_lines.append(f"**primary_topic が変わった件数：** {n_changed} / {len(rows)} 件")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    for i, r in enumerate(rows, 1):
        md_lines.append(f"## {i}. {short(r['title'], 80)}")
        md_lines.append("")
        md_lines.append(f"- **Work ID:** [{r['work_id']}]({r['work_id']})")
        md_lines.append("")
        md_lines.append("| | 既存 OpenAlex | 本手法 |")
        md_lines.append("|---|---|---|")
        md_lines.append(f"| primary_topic | {short(r['existing_primary'])} | {short(r['ours_primary'])} {'**(変更)**' if r['primary_changed'] else '(同じ)'} |")
        md_lines.append(f"| topics[1] | {short(r['existing_topic_2'])} | {short(r['ours_topic_2'])} |")
        md_lines.append(f"| topics[2] | {short(r['existing_topic_3'])} | {short(r['ours_topic_3'])} |")
        md_lines.append("")
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"Wrote {args.out_md}", file=sys.stderr)

    print(f"\nSummary: primary_topic changed in {n_changed}/{len(rows)} works.", file=sys.stderr)


if __name__ == "__main__":
    main()
