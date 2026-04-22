"""
FastAPI web application for IRDB Topic Matcher.

Start with:
    uvicorn web.app:app --reload --app-dir /path/to/irdb-topic-matcher
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.embeddings import EmbeddingModel, ModelType
from src.ndc_mapping import NDCMapper
from src.topic_index import TopicIndex
from src.topic_matcher import TopicMatcher

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="IRDB Topic Matcher", version="1.0.0")

TEMPLATES_DIR = Path(__file__).parent / "templates"
INDEX_DIR = ROOT / "index"
CACHE_PATH = ROOT / "data" / "topics_cache.json"

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

_matcher: TopicMatcher | None = None
_index_status: dict = {"state": "unknown", "message": "", "progress": 0}


def _get_matcher() -> TopicMatcher:
    global _matcher
    if _matcher is None:
        if not (INDEX_DIR / "topics.faiss").exists():
            raise HTTPException(status_code=503, detail="Index not built yet. Please build the index first.")
        _matcher = TopicMatcher.load(INDEX_DIR)
    return _matcher


def _reset_matcher() -> None:
    global _matcher
    _matcher = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse((TEMPLATES_DIR / "index.html").read_text())


@app.get("/api/status")
async def get_status():
    index_ready = (INDEX_DIR / "topics.faiss").exists()
    topic_count = 0
    if index_ready:
        meta = INDEX_DIR / "topics_meta.json"
        if meta.exists():
            topic_count = len(json.loads(meta.read_text()))
    return {
        "index_ready": index_ready,
        "topic_count": topic_count,
        "build_status": _index_status,
    }


# ---------------------------------------------------------------------------
# Single-paper matching
# ---------------------------------------------------------------------------

class MatchRequest(BaseModel):
    title: str
    abstract: str = ""
    ndc_codes: list[str] = []
    model: str = ModelType.MULTILINGUAL_E5.value
    threshold: float = 0.5
    top_k: int = 5


@app.post("/api/match")
async def match_paper(req: MatchRequest):
    matcher = _get_matcher()
    result = matcher.match(
        title=req.title,
        abstract=req.abstract,
        ndc_codes=req.ndc_codes or None,
    )
    return {
        "topic_id": result.topic_id,
        "topic_name": result.topic_name,
        "field": result.field,
        "subfield": result.subfield,
        "domain": result.domain,
        "confidence": round(result.confidence, 4),
        "method": result.method,
        "candidates": [
            {
                "topic_id": c.topic_id,
                "topic_name": c.display_name,
                "field": c.field,
                "subfield": c.subfield,
                "score": round(c.score, 4),
            }
            for c in result.candidates
        ],
        "ndc_match": {
            "code": result.ndc_match.ndc_code,
            "matched_prefix": result.ndc_match.matched_prefix,
            "field": result.ndc_match.field,
            "subfield": result.ndc_match.subfield,
        } if result.ndc_match else None,
    }


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

@app.post("/api/batch")
async def batch_process(
    file: UploadFile = File(...),
    threshold: float = Form(0.5),
    top_k: int = Form(5),
):
    matcher = _get_matcher()

    content = await file.read()
    text = content.decode("utf-8").strip()
    try:
        if text.startswith("["):
            records = json.loads(text)
        else:
            records = [json.loads(line) for line in text.splitlines() if line.strip()]
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if not records:
        raise HTTPException(status_code=400, detail="Empty input file.")
    if len(records) > 5000:
        raise HTTPException(status_code=400, detail="Maximum 5,000 records per batch.")

    results = matcher.match_batch(records)
    output_lines = []
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
        output_lines.append(json.dumps(enriched, ensure_ascii=False))

    output = "\n".join(output_lines)
    return StreamingResponse(
        iter([output]),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": "attachment; filename=results.jsonl"},
    )


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

class BuildRequest(BaseModel):
    model: str = ModelType.MULTILINGUAL_E5.value
    mailto: str = ""


async def _build_index_task(model_str: str, mailto: str) -> None:
    global _index_status
    _index_status = {"state": "running", "message": "モデルを読み込み中…", "progress": 5}
    try:
        loop = asyncio.get_event_loop()

        def _blocking_build():
            model = EmbeddingModel(model_type=model_str)
            _index_status["message"] = "OpenAlex Topicsを取得中…"
            _index_status["progress"] = 20
            from src.topic_index import TopicIndex
            index = TopicIndex.build(model=model, cache_path=CACHE_PATH, mailto=mailto)
            _index_status["message"] = "FAISSインデックスを保存中…"
            _index_status["progress"] = 90
            index.save(INDEX_DIR)
            return len(index.topics)

        count = await loop.run_in_executor(None, _blocking_build)
        _index_status = {
            "state": "done",
            "message": f"{count:,} トピックのインデックスを構築しました",
            "progress": 100,
        }
        _reset_matcher()
    except Exception as e:
        _index_status = {"state": "error", "message": str(e), "progress": 0}


@app.post("/api/build-index")
async def build_index(req: BuildRequest, background_tasks: BackgroundTasks):
    if _index_status.get("state") == "running":
        return JSONResponse(status_code=409, content={"detail": "インデックス構築が既に実行中です"})
    background_tasks.add_task(_build_index_task, req.model, req.mailto)
    return {"message": "インデックス構築を開始しました"}
