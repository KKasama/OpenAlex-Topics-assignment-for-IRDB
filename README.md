> [!WARNING]
> **このリポジトリは v1（アーカイブ版）です。最新版の v2（アンサンブル版：埋め込み + BM25）は [OpenAlex-Topics-assignment-for-IRDB2](https://github.com/KKasama/OpenAlex-Topics-assignment-for-IRDB2) をご利用ください。**

# OpenAlex Topics Assignment for IRDB

A tool to improve Topic assignments for Japanese bibliographic records (IRDB) ingested into OpenAlex, using embedding-based matching and NDC code mapping.

---

## Problem

When Japanese bibliographic data from IRDB is ingested into OpenAlex, Topic assignments are often incorrect or inconsistent due to:
- Language mismatch (Japanese titles/abstracts vs. English topic labels)
- Missing abstracts
- Absence of citation network data

---

## Solution

### Step 1 — Embedding-Based Topic Matching

Each paper's title and abstract are encoded into a dense vector using a multilingual or domain-adapted language model:

| Model | Best for |
|---|---|
| `intfloat/multilingual-e5-large` | Japanese text (recommended) |
| `allenai/specter2_base` | Citation-aware academic embeddings |

Representative vectors for all ~4,500 OpenAlex Topics (title + description + keywords) are pre-computed and stored in a **FAISS** index. For each paper, the top-K most similar topics are retrieved by cosine similarity.

### Step 2 — NDC → Field/Subfield Mapping

Japanese records commonly carry **NDC (Nippon Decimal Classification)** codes. A mapping table links NDC codes to OpenAlex Fields and Subfields. This provides a rule-based re-ranking signal or fallback when embedding confidence is low.

**Assignment logic:**
1. Retrieve Top-K candidates via embedding similarity
2. If NDC codes are present → boost candidates whose Field/Subfield matches the NDC mapping (+0.05)
3. If confidence < threshold → fall back to NDC mapping directly

---

## Project Structure

```
irdb-topic-matcher/
├── src/
│   ├── embeddings.py          # multilingual-e5 / SPECTER2 wrapper
│   ├── openalex_client.py     # OpenAlex Topics API client
│   ├── topic_index.py         # FAISS index build & query
│   ├── ndc_mapping.py         # NDC → Field/Subfield lookup
│   └── topic_matcher.py       # Main matching pipeline
├── data/
│   └── ndc_openalex_mapping.json  # NDC mapping table
├── web/
│   ├── app.py                 # FastAPI web application
│   └── templates/index.html   # Single-page UI (JA/EN)
├── scripts/
│   ├── build_index.py         # CLI: build FAISS index
│   └── assign_topics.py       # CLI: assign topics to JSONL records
└── requirements.txt
```

---

## Setup

```bash
# Clone
git clone https://github.com/KKasama/OpenAlex-Topics-assignment-for-IRDB.git
cd OpenAlex-Topics-assignment-for-IRDB

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Web Interface

```bash
python3 -m uvicorn web.app:app --reload
# Open http://localhost:8000
```

The UI supports **Japanese / English** switching and provides three tabs:

| Tab | Function |
|---|---|
| Single Paper | Enter title, abstract, NDC codes → get topic assignment |
| Batch | Upload JSONL file (up to 5,000 records) → download results |
| Index | Build / manage the FAISS topic index |

**First run:** Go to the **Index** tab and click **Build Index**. This fetches ~4,500 topics from the OpenAlex API and builds the FAISS index (takes a few minutes).

---

## CLI Usage

```bash
# Build index (first time only)
python scripts/build_index.py --index-dir ./index --mailto your@email.com

# Assign topics to a JSONL file
python scripts/assign_topics.py --index-dir ./index \
  --input records.jsonl --output results.jsonl
```

### Input format

```jsonl
{"title": "深層学習による画像認識", "abstract": "...", "ndc_codes": ["007", "548"]}
{"title": "日本の農業生産性に関する研究", "ndc_codes": ["610"], "language": "ja"}
{"title": "First M87 Event Horizon Telescope Results", "abstract": "...", "language": "eng"}
```

The optional `language` field (e.g. `"ja"`, `"jpn"`, `"eng"`) is honored when
present; otherwise language is inferred from kana / CJK characters in the title
and abstract.

### Japanese-only mode (default)

By default, only Japanese records are re-assigned. Non-Japanese records pass
through unchanged so existing OpenAlex Topic assignments are preserved. To
process every record regardless of language, pass `--no-japanese-only`:

```bash
python scripts/assign_topics.py --index-dir ./index \
  --input records.jsonl --output results.jsonl --no-japanese-only
```

The web UI exposes the same toggle on the Single Paper and Batch tabs.

### Output format

Japanese records are enriched with the following added fields. Non-Japanese
records are written through unchanged.

```json
{
  "title": "...",
  "topic_id": "https://openalex.org/T...",
  "topic_name": "Machine Learning",
  "field": "Computer Science",
  "subfield": "Artificial Intelligence",
  "domain": "Physical Sciences",
  "confidence": 0.823,
  "method": "embedding"
}
```

`method` values: `embedding` | `ndc_rerank` | `ndc_fallback`

---

## Requirements

- Python 3.9+
- ~4 GB disk for model weights (`multilingual-e5-large`)
- Internet access for first-time OpenAlex Topics fetch

---

## License

MIT
