"""
Input / output adapters for batch processing.

Supports two file formats:

* **JSONL / JSON** — the project's native format.
* **OpenAlex Works CSV** — the flat CSV export produced by openalex.org's
  bulk download. Maps ``display_name`` -> title, ``abstract`` -> abstract,
  ``language`` -> language. The original columns are preserved on output and
  the new Topic columns (``topic_id``, ``topic_name``, ``field``, ``subfield``,
  ``domain``, ``confidence``, ``method``) are appended.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Iterable, Iterator

# Column name -> matcher input key. Order matters for fallback (first hit wins).
_CSV_TITLE_KEYS = ("display_name", "title")
_CSV_ABSTRACT_KEYS = ("abstract",)
_CSV_LANGUAGE_KEYS = ("language",)
# A few exporters include NDC under variant names; collect any that look like NDC.
_CSV_NDC_KEYS = ("ndc_codes", "ndc", "ndc_code")

_OUTPUT_COLUMNS = [
    "topic_id",
    "topic_name",
    "field",
    "subfield",
    "domain",
    "confidence",
    "method",
]


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def is_csv_filename(filename: str | None) -> bool:
    return bool(filename) and filename.lower().endswith(".csv")


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def _first(row: dict, keys: Iterable[str]) -> str:
    for k in keys:
        if k in row and row[k] is not None:
            v = str(row[k]).strip()
            if v:
                return v
    return ""


def _split_ndc(value: str) -> list[str]:
    if not value:
        return []
    # Allow ``;`` ``|`` or ``,`` separators (common in OpenAlex flat CSV arrays).
    for sep in ("|", ";"):
        value = value.replace(sep, ",")
    return [c.strip() for c in value.split(",") if c.strip()]


def csv_text_to_records(text: str) -> tuple[list[dict], list[dict], list[str]]:
    """Parse OpenAlex Works CSV text.

    Returns ``(matcher_inputs, original_rows, fieldnames)`` where:

    * ``matcher_inputs`` is the list of ``{title, abstract, language, ndc_codes}``
      dicts to feed into ``TopicMatcher.match_batch``.
    * ``original_rows`` is the full original row preserved for output.
    * ``fieldnames`` is the original column order.
    """
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV has no header row.")

    fieldnames = list(reader.fieldnames)
    matcher_inputs: list[dict] = []
    original_rows: list[dict] = []
    for row in reader:
        original_rows.append(dict(row))
        matcher_inputs.append(
            {
                "title": _first(row, _CSV_TITLE_KEYS),
                "abstract": _first(row, _CSV_ABSTRACT_KEYS),
                "language": _first(row, _CSV_LANGUAGE_KEYS) or None,
                "ndc_codes": _split_ndc(_first(row, _CSV_NDC_KEYS)) or None,
            }
        )
    return matcher_inputs, original_rows, fieldnames


def write_csv_rows(
    fieldnames: list[str],
    rows: Iterable[dict],
) -> Iterator[str]:
    """Stream CSV output one row at a time.

    The output schema is the original ``fieldnames`` plus :data:`_OUTPUT_COLUMNS`.
    For records with ``method == "skipped"``, the new columns are left blank so
    the original ``primary_topic.display_name`` (and friends) are preserved
    untouched.
    """
    out_columns = list(fieldnames) + [
        c for c in _OUTPUT_COLUMNS if c not in fieldnames
    ]

    header_buf = io.StringIO()
    csv.writer(header_buf).writerow(out_columns)
    yield header_buf.getvalue()

    for row in rows:
        buf = io.StringIO()
        csv.DictWriter(buf, fieldnames=out_columns, extrasaction="ignore").writerow(row)
        yield buf.getvalue()


def enrich_row(original: dict, result, *, skipped: bool) -> dict:
    """Merge a matcher result into the original CSV row."""
    if skipped:
        return original  # Pass through with no new columns populated.
    return {
        **original,
        "topic_id": result.topic_id,
        "topic_name": result.topic_name,
        "field": result.field,
        "subfield": result.subfield,
        "domain": result.domain,
        "confidence": round(result.confidence, 4),
        "method": result.method,
    }


# ---------------------------------------------------------------------------
# JSONL / JSON
# ---------------------------------------------------------------------------

def jsonl_text_to_records(text: str) -> list[dict]:
    text = text.strip()
    if not text:
        return []
    if text.startswith("["):
        return json.loads(text)
    out: list[dict] = []
    for i, line in enumerate(text.split("\n"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"Line {i}: invalid JSON — {e}") from e
    return out
