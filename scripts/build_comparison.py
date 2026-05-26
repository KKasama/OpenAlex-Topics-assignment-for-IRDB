#!/usr/bin/env python3
"""
Build a side-by-side comparison between the existing OpenAlex Topic
assignment and the Topic re-assignment produced by this project.

Reads the local topics JSONL, picks a sample of work IDs that have
Japanese titles, fetches each Work's existing ``primary_topic`` / ``topics``
from OpenAlex, and emits a Markdown + CSV table for inclusion in
reports / cover letters.

Usage
-----
    export OPENALEX_API_KEY=...        # optional, Premium tier
    python scripts/build_comparison.py \
        --input    data/topics-irdb-ja-multi.jsonl \
        --works-in data/works-irdb-ja.jsonl \
        --sample 10 \
        --mailto your@example.org \
        --out-md  docs/comparison-ja.md \
        --out-csv docs/comparison-ja.csv
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OPENALEX_BASE = "https://api.openalex.org/works"

# 日本語文字（ひらがな・カタカナ・CJK統合漢字）を含むか判定
_JP_RE = re.compile(r'[぀-ゟ゠-ヿ一-鿿]')


def is_japanese_title(title: str) -> bool:
    return bool(_JP_RE.search(title or ""))


def fetch_work(work_url: str, mailto: str, api_key: str | None) -> dict:
    """Fetch a single Work record. Returns the JSON dict."""
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
    p.add_argument("--input",    default="data/topics-irdb-ja-multi.jsonl")
    p.add_argument("--works-in", default="data/works-irdb-ja.jsonl",
                   help="元の Works JSONL（タイトル取得・日本語フィルタ用）")
    p.add_argument("--sample", type=int, default=10)
    p.add_argument("--mailto", required=True)
    p.add_argument("--out-md",  default="docs/comparison-ja.md")
    p.add_argument("--out-csv", default="docs/comparison-ja.csv")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    api_key = os.environ.get("OPENALEX_API_KEY")

    # ── Works メタデータ（タイトル）を読み込む ──────────────────
    print(f"Loading works titles from {args.works_in} ...", file=sys.stderr)
    work_titles: dict[str, str] = {}
    with open(args.works_in, encoding="utf-8") as f:
        for line in f:
            w = json.loads(line)
            work_titles[w["id"]] = w.get("title") or ""
    print(f"  Loaded {len(work_titles):,} works", file=sys.stderr)

    # ── 本手法の結果を読み込み、日本語タイトルのみに絞る ────────
    print(f"Loading topic assignments from {args.input} ...", file=sys.stderr)
    ours_all: list[dict] = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            ours_all.append(json.loads(line))

    ours_ja = [
        rec for rec in ours_all
        if is_japanese_title(work_titles.get(rec["work_id"], ""))
    ]
    print(f"  Total: {len(ours_all):,} / Japanese-title: {len(ours_ja):,}", file=sys.stderr)

    # ── サンプリング ─────────────────────────────────────────────
    rnd = random.Random(args.seed)
    picks = rnd.sample(ours_ja, min(args.sample, len(ours_ja)))
    print(f"Sampling {len(picks)} Japanese-title works for comparison", file=sys.stderr)

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
            "title_ja": work_titles.get(work_id, ""),          # 日本語タイトル
            "title_en": w.get("display_name", ""),             # OpenAlex 表示名
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
    md_lines.append("# 改善比較表（既存 OpenAlex vs 本手法、日本語論文サンプル）")
    md_lines.append("")
    md_lines.append(f"**サンプル件数：** {len(rows)} 件（日本語タイトル論文から無作為抽出、seed={args.seed}）")
    md_lines.append("")
    n_changed = sum(1 for r in rows if r["primary_changed"])
    md_lines.append(f"**primary_topic が変わった件数：** {n_changed} / {len(rows)} 件")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    for i, r in enumerate(rows, 1):
        # タイトル：日本語タイトルを優先表示
        display_title = r["title_ja"] or r["title_en"] or r["work_id"]
        md_lines.append(f"## {i}. {short(display_title, 80)}")
        md_lines.append("")
        md_lines.append(f"- **Work ID:** [{r['work_id']}]({r['work_id']})")
        if r["title_ja"] and r["title_en"] and r["title_ja"] != r["title_en"]:
            md_lines.append(f"- **タイトル（日）：** {short(r['title_ja'], 100)}")
            md_lines.append(f"- **Title (EN)：** {short(r['title_en'], 100)}")
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
