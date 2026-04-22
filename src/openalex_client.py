"""
OpenAlex API client — fetches Topics with their keywords and descriptions.

OpenAlex Topics API: https://docs.openalex.org/api-entities/topics
Each topic has: id, display_name, description, keywords, field, subfield, domain
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterator

import requests

_BASE_URL = "https://api.openalex.org"
_PAGE_SIZE = 200


def _get(url: str, params: dict) -> dict:
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def iter_topics(mailto: str = "") -> Iterator[dict]:
    """Paginate through all OpenAlex Topics and yield each topic dict."""
    params: dict = {
        "per-page": _PAGE_SIZE,
        "cursor": "*",
        "select": "id,display_name,description,keywords,field,subfield,domain",
    }
    if mailto:
        params["mailto"] = mailto

    while True:
        data = _get(f"{_BASE_URL}/topics", params)
        for item in data["results"]:
            yield item
        next_cursor = data["meta"].get("next_cursor")
        if not next_cursor:
            break
        params["cursor"] = next_cursor
        time.sleep(0.1)  # polite rate limit


def fetch_all_topics(cache_path: str | Path, mailto: str = "") -> list[dict]:
    """Return all topics, loading from cache_path if it exists."""
    cache = Path(cache_path)
    if cache.exists():
        return json.loads(cache.read_text())

    topics = list(iter_topics(mailto=mailto))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(topics, ensure_ascii=False, indent=2))
    return topics


def topic_text(topic: dict) -> str:
    """Compose a single string representing a topic for embedding."""
    parts = [topic.get("display_name", "")]
    if desc := topic.get("description"):
        parts.append(desc)
    if kws := topic.get("keywords"):
        parts.append(", ".join(kws))
    return " | ".join(filter(None, parts))
