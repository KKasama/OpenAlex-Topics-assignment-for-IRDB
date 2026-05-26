#!/usr/bin/env python3
"""
武田先生コメント対応：信頼度スコアの深掘り分析
=================================================
以下の5点を集計して Markdown レポートを出力する。

1. Primary Topic 上位20件 ─ 階層情報＋スコア分布
2. Primary Topic 下位20件 ─ 同上
3. SubField 単位のスコア分布集計
4. 入力情報の質（要旨有無 × タイトル長）による比較
5. スコア帯の件率（quality-report の空欄埋め）

Usage
-----
    python scripts/deep_analysis.py \
        --topics-out  data/topics-irdb-ja-multi.jsonl \
        --works-in    data/works-irdb-ja.jsonl \
        --meta        index-base/topics_meta.json \
        --out-md      docs/deep-analysis.md \
        --title-threshold 30
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


# ── 統計ユーティリティ ────────────────────────────────────────────
def stats(values: list[float]) -> dict:
    if not values:
        return dict(n=0, mean="-", median="-", std="-", min="-", max="-")
    return dict(
        n=len(values),
        mean=statistics.mean(values),
        median=statistics.median(values),
        std=statistics.stdev(values) if len(values) > 1 else 0.0,
        min=min(values),
        max=max(values),
    )


def fmt(v, digits=4) -> str:
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return str(v)


def stats_row(s: dict) -> str:
    """Markdown table row: n | mean | median | std | min | max"""
    return (
        f"{s['n']:,} | {fmt(s['mean'])} | {fmt(s['median'])} | "
        f"{fmt(s['std'])} | {fmt(s['min'])} | {fmt(s['max'])}"
    )


# ── メイン ───────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topics-out",  default="data/topics-irdb-ja-multi.jsonl")
    ap.add_argument("--works-in",    default="data/works-irdb-ja.jsonl")
    ap.add_argument("--meta",        default="index-base/topics_meta.json")
    ap.add_argument("--out-md",      default="docs/deep-analysis.md")
    ap.add_argument("--title-threshold", type=int, default=30,
                    help="タイトル文字数の長短閾値（デフォルト 30 字）")
    args = ap.parse_args()

    THR = args.title_threshold

    # ── 1. Topic メタデータ読み込み ──────────────────────────────
    print("Loading topic metadata...")
    with open(args.meta, encoding="utf-8") as f:
        meta_list = json.load(f)
    topic_meta: dict[str, dict] = {t["id"]: t for t in meta_list}

    # ── 2. 入力 Works 読み込み（id → title_len, has_abstract）───
    print("Loading works metadata (title/abstract)...")
    work_info: dict[str, tuple[int, bool]] = {}
    with open(args.works_in, encoding="utf-8") as f:
        for line in f:
            w = json.loads(line)
            wid = w.get("id", "")
            title = w.get("title") or ""
            abstract = w.get("abstract") or ""
            work_info[wid] = (len(title), bool(abstract.strip()))

    print(f"  Loaded {len(work_info):,} works")

    # ── 3. 出力 JSONL をストリーム集計 ───────────────────────────
    print("Streaming topics output...")

    scores_all: list[float] = []
    topic_scores:    dict[str, list[float]] = defaultdict(list)  # topic_id → scores
    subfield_scores: dict[str, list[float]] = defaultdict(list)  # subfield name → scores

    # 入力品質パターン： (has_abstract, long_title) → scores
    quality_scores: dict[tuple, list[float]] = defaultdict(list)

    with open(args.topics_out, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i % 200_000 == 0:
                print(f"  {i:,} records processed...")
            r = json.loads(line)
            pt = r.get("primary_topic") or {}
            score = pt.get("score")
            topic_id = pt.get("id", "")
            work_id  = r.get("work_id", "")

            if score is None:
                continue

            scores_all.append(score)
            topic_scores[topic_id].append(score)

            # SubField
            meta = topic_meta.get(topic_id, {})
            sf = (meta.get("subfield") or {}).get("display_name", "Unknown")
            subfield_scores[sf].append(score)

            # 入力品質
            title_len, has_abs = work_info.get(work_id, (0, False))
            long_title = title_len > THR
            quality_scores[(has_abs, long_title)].append(score)

    print(f"  Total: {len(scores_all):,} records")

    # ── 4. 上位 / 下位 20 Topics ─────────────────────────────────
    topic_count = Counter({tid: len(sc) for tid, sc in topic_scores.items()})
    top20    = topic_count.most_common(20)
    bottom20 = topic_count.most_common()[:-21:-1]  # 最小 20 件

    # ── 5. SubField 集計（件数順） ────────────────────────────────
    sf_count = sorted(subfield_scores.items(), key=lambda x: -len(x[1]))

    # ── 6. スコア帯の件率 ─────────────────────────────────────────
    bands = [
        ("0.85 以上",   lambda s: s >= 0.85),
        ("0.80〜0.85",  lambda s: 0.80 <= s < 0.85),
        ("0.75〜0.80",  lambda s: 0.75 <= s < 0.80),
        ("0.70〜0.75",  lambda s: 0.70 <= s < 0.75),
        ("0.65〜0.70",  lambda s: 0.65 <= s < 0.70),
        ("0.65 未満",   lambda s: s < 0.65),
    ]
    total = len(scores_all)

    # ── Markdown 出力 ─────────────────────────────────────────────
    lines: list[str] = []

    def h(level: int, text: str):
        lines.append(f"\n{'#' * level} {text}\n")

    def p(text: str):
        lines.append(text)

    lines.append("# 信頼度スコア深掘り分析レポート")
    lines.append("## IRDB 日本語論文 OpenAlex Topic 再付与 — multilingual-e5-base\n")
    lines.append(f"**作成日：** 2026 年 5 月 26 日  ")
    lines.append(f"**対象件数：** {total:,} 件  ")
    lines.append(f"**タイトル長短閾値：** {THR} 文字\n")
    lines.append("---\n")

    # ── セクション 1 & 2：上位／下位 20 Topics ────────────────────
    for label, top_list in [("上位", top20), ("下位", bottom20)]:
        h(2, f"1{'a' if label=='上位' else 'b'}. Primary Topic {label} 20 件：階層情報とスコア分布")
        p(f"> 各 Topic の OpenAlex 階層（Domain / Field / Subfield）とスコア統計量（件数・平均・中央値・標準偏差・最小・最大）。\n")
        p("| 件数 | Topic | Domain | Field | Subfield | 平均 | 中央値 | 標準偏差 | 最小 | 最大 |")
        p("|---:|---|---|---|---|---:|---:|---:|---:|---:|")
        for tid, cnt in top_list:
            sc = topic_scores[tid]
            s  = stats(sc)
            m  = topic_meta.get(tid, {})
            name   = m.get("display_name", tid)
            domain = (m.get("domain")    or {}).get("display_name", "—")
            field  = (m.get("field")     or {}).get("display_name", "—")
            sf     = (m.get("subfield")  or {}).get("display_name", "—")
            p(f"| {cnt:,} | {name} | {domain} | {field} | {sf} | "
              f"{fmt(s['mean'])} | {fmt(s['median'])} | {fmt(s['std'])} | "
              f"{fmt(s['min'])} | {fmt(s['max'])} |")
        lines.append("")

    # ── セクション 3：SubField 単位 ───────────────────────────────
    h(2, "2. SubField 単位のスコア分布（件数上位 30 SubField）")
    p("> SubField（OpenAlex タクソノミー第 3 階層）ごとのスコア統計量。件数上位 30 を表示。\n")
    p("| 件数 | SubField | 平均 | 中央値 | 標準偏差 | 最小 | 最大 |")
    p("|---:|---|---:|---:|---:|---:|---:|")
    for sf_name, sc in sf_count[:30]:
        s = stats(sc)
        p(f"| {len(sc):,} | {sf_name} | {fmt(s['mean'])} | {fmt(s['median'])} | "
          f"{fmt(s['std'])} | {fmt(s['min'])} | {fmt(s['max'])} |")
    lines.append("")

    # ── セクション 4：入力品質による比較 ─────────────────────────
    h(2, f"3. 入力情報の質によるスコア比較（閾値：タイトル {THR} 文字）")
    p("> 各 Work を「要旨の有無」×「タイトルの長短」の 4 パターンに分けてスコア分布を比較。\n")
    p("| パターン | 要旨 | タイトル | 件数 | 平均 | 中央値 | 標準偏差 | 最小 | 最大 |")
    p("|---|:---:|:---:|---:|---:|---:|---:|---:|---:|")
    patterns = [
        (True,  True,  "A", f"あり", f"長 (>{THR}字)"),
        (True,  False, "B", f"あり", f"短 (≤{THR}字)"),
        (False, True,  "C", f"なし", f"長 (>{THR}字)"),
        (False, False, "D", f"なし", f"短 (≤{THR}字)"),
    ]
    for has_abs, long_t, pat, abs_label, tit_label in patterns:
        sc = quality_scores.get((has_abs, long_t), [])
        s  = stats(sc)
        p(f"| パターン {pat} | {abs_label} | {tit_label} | {s['n']:,} | "
          f"{fmt(s['mean'])} | {fmt(s['median'])} | {fmt(s['std'])} | "
          f"{fmt(s['min'])} | {fmt(s['max'])} |")
    lines.append("")
    p("> **解釈のポイント：** 要旨あり・長タイトルのパターン A が最も高スコアになることが期待されます。"
      "パターン D（要旨なし・短タイトル）との差が大きい場合、入力情報の質がスコアに有意な影響を与えていることを示します。\n")

    # ── セクション 5：スコア帯の件率 ─────────────────────────────
    h(2, "4. スコア帯の件率（品質レポート補完）")
    p("> `quality-report-full.md` で空欄だった「本データの件率」を補完。\n")
    p("| スコア帯 | 解釈 | 件数 | 件率 |")
    p("|---|---|---:|---:|")
    interp = {
        "0.85 以上":  "非常に強いマッチ",
        "0.80〜0.85": "強いマッチ（上位層）",
        "0.75〜0.80": "強いマッチ（主要分布帯）",
        "0.70〜0.75": "中程度のマッチ",
        "0.65〜0.70": "弱めのマッチ",
        "0.65 未満":  "弱いマッチ",
    }
    for band_label, cond in bands:
        cnt = sum(1 for s in scores_all if cond(s))
        pct = cnt / total * 100
        p(f"| {band_label} | {interp[band_label]} | {cnt:,} | **{pct:.1f} %** |")
    lines.append("")

    # ── 全件スコア統計（再掲） ─────────────────────────────────────
    h(2, "5. 全件スコア統計（再掲）")
    s_all = stats(scores_all)
    p("| 統計量 | 値 |")
    p("|---|---|")
    for k, v in s_all.items():
        p(f"| {k} | {fmt(v) if isinstance(v, float) else f'{v:,}'} |")
    lines.append("")
    lines.append("---\n")
    lines.append("*本レポートは `scripts/deep_analysis.py` により自動生成されました。*")

    # ── ファイル書き出し ──────────────────────────────────────────
    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nWrote {args.out_md}")


if __name__ == "__main__":
    main()
