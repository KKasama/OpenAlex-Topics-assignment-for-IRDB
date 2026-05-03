"""
Light-weight Japanese-language detection for IRDB records.

Two signals, in priority order:
  1. Explicit ``language`` field on the record (ISO 639-1 / 639-2 codes).
  2. Presence of Japanese kana (Hiragana / Katakana) in ``title`` + ``abstract``.

Records whose body contains only Latin characters are treated as non-Japanese.
Records that contain only CJK ideographs (no kana) are treated as Japanese in
the IRDB context — pure-kanji Japanese titles are common, while pure-kanji
Chinese records are out of scope for IRDB ingestion.
"""

from __future__ import annotations

import re

# ISO codes and common synonyms that mean "Japanese".
_JA_LANG_CODES: frozenset[str] = frozenset(
    {"ja", "jpn", "jp", "japanese", "ja-jp", "ja_jp"}
)

_HIRAGANA_RE = re.compile(r"[぀-ゟ]")
_KATAKANA_RE = re.compile(r"[゠-ヿㇰ-ㇿ]")
# CJK Unified Ideographs (Basic + Extension A).
_CJK_RE = re.compile(r"[一-鿿㐀-䶿]")


def normalize_language(language: str | None) -> str | None:
    if not language:
        return None
    return language.strip().lower()


def is_japanese(
    title: str = "",
    abstract: str = "",
    language: str | None = None,
) -> bool:
    """Return ``True`` if the record looks like a Japanese paper.

    Priority:
      1. Explicit ``language`` (e.g. ``"ja"``, ``"jpn"``) — authoritative.
      2. Hiragana or Katakana in title/abstract — definitive Japanese marker.
      3. CJK-only text — assumed Japanese (IRDB context).
      4. Otherwise — not Japanese.
    """
    lang = normalize_language(language)
    if lang is not None:
        return lang in _JA_LANG_CODES

    text = f"{title or ''}\n{abstract or ''}"
    if _HIRAGANA_RE.search(text) or _KATAKANA_RE.search(text):
        return True
    if _CJK_RE.search(text):
        return True
    return False
