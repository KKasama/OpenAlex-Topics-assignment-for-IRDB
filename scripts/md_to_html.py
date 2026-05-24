#!/usr/bin/env python3
"""Convert one or more Markdown files into self-contained HTML pages
that print to PDF nicely from Safari/Chrome on macOS.

Usage
-----
    python scripts/md_to_html.py docs/technical-memo-for-Prof_takeda.md
    # → docs/technical-memo-for-Prof_takeda.html

    python scripts/md_to_html.py docs/*.md
    # → one .html next to each .md
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

import markdown  # type: ignore


CSS = """
@page {
    size: A4;
    margin: 18mm 16mm;
}
:root {
    --fg: #1f2328;
    --muted: #57606a;
    --accent: #0969da;
    --border: #d0d7de;
    --bg-soft: #f6f8fa;
}
* { box-sizing: border-box; }
body {
    font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN",
                 -apple-system, "Helvetica Neue", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.7;
    color: var(--fg);
    max-width: 760px;
    margin: 0 auto;
    padding: 24px 24px 64px;
}
h1, h2, h3, h4 {
    font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN",
                 -apple-system, sans-serif;
    line-height: 1.35;
    margin-top: 1.6em;
    margin-bottom: 0.6em;
}
h1 {
    font-size: 22pt;
    border-bottom: 2px solid var(--border);
    padding-bottom: 0.3em;
    margin-top: 0.3em;
}
h2 {
    font-size: 16pt;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.25em;
}
h3 { font-size: 13pt; }
h4 { font-size: 11.5pt; color: var(--muted); }

p, ul, ol { margin: 0.6em 0; }
ul, ol { padding-left: 1.4em; }
li { margin: 0.15em 0; }

code {
    font-family: "SF Mono", "Menlo", monospace;
    font-size: 0.9em;
    background: var(--bg-soft);
    padding: 0.1em 0.35em;
    border-radius: 4px;
}
pre {
    background: var(--bg-soft);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 12px;
    overflow-x: auto;
    font-size: 9pt;
    line-height: 1.5;
    page-break-inside: avoid;
}
pre code {
    background: transparent;
    padding: 0;
}
blockquote {
    border-left: 4px solid var(--border);
    padding: 0.2em 0.9em;
    color: var(--muted);
    margin: 0.8em 0;
    background: var(--bg-soft);
    border-radius: 0 4px 4px 0;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 0.8em 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}
th, td {
    border: 1px solid var(--border);
    padding: 5px 8px;
    text-align: left;
    vertical-align: top;
}
th { background: var(--bg-soft); font-weight: 600; }
tr:nth-child(even) td { background: #fafbfc; }

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
hr { border: 0; border-top: 1px solid var(--border); margin: 1.5em 0; }

/* Print tweaks */
@media print {
    body { padding: 0; }
    h1, h2, h3, h4 { page-break-after: avoid; }
    pre, table, blockquote { page-break-inside: avoid; }
}
"""


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


def convert(md_path: Path) -> Path:
    text = md_path.read_text(encoding="utf-8")
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"],
        output_format="html5",
    )
    title = md_path.stem
    out = HTML_TEMPLATE.format(title=html.escape(title), css=CSS, body=body)
    out_path = md_path.with_suffix(".html")
    out_path.write_text(out, encoding="utf-8")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", help="Markdown files to convert")
    args = ap.parse_args()

    for inp in args.inputs:
        p = Path(inp)
        if not p.exists():
            print(f"  skip (not found): {p}", file=sys.stderr)
            continue
        out = convert(p)
        print(f"  wrote {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
