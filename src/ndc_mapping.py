"""
NDC (Nippon Decimal Classification) → OpenAlex Field/Subfield/Domain lookup.

Lookup is hierarchical: tries the full code first, then progressively shorter
prefixes so that e.g. "512" falls back to "51" then "5".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_TABLE = Path(__file__).parent.parent / "data" / "ndc_openalex_mapping.json"


@dataclass
class NDCMatch:
    ndc_code: str
    matched_prefix: str
    field: str
    subfield: str
    domain: str


class NDCMapper:
    def __init__(self, table_path: str | Path = _DEFAULT_TABLE) -> None:
        self._table: dict[str, dict] = json.loads(Path(table_path).read_text())

    def lookup(self, ndc_code: str) -> NDCMatch | None:
        """
        Look up a single NDC code.

        The code may be formatted as "510", "51", "NDC:510", "NDC 510", etc.
        Returns None if no mapping is found.
        """
        code = _normalize_ndc(ndc_code)
        if not code:
            return None

        # Try from most specific (3-digit) down to 1-digit
        for length in range(min(len(code), 3), 0, -1):
            prefix = code[:length]
            if prefix in self._table:
                entry = self._table[prefix]
                return NDCMatch(
                    ndc_code=code,
                    matched_prefix=prefix,
                    field=entry["field"],
                    subfield=entry["subfield"],
                    domain=entry["domain"],
                )
        return None

    def lookup_many(self, ndc_codes: list[str]) -> list[NDCMatch]:
        """Look up a list of NDC codes and return successful matches."""
        results = []
        for code in ndc_codes:
            match = self.lookup(code)
            if match:
                results.append(match)
        return results

    def best_match(self, ndc_codes: list[str]) -> NDCMatch | None:
        """
        Return the most specific match across multiple NDC codes.
        Prefers longer matched_prefix (more specific classification).
        """
        matches = self.lookup_many(ndc_codes)
        if not matches:
            return None
        return max(matches, key=lambda m: len(m.matched_prefix))


def _normalize_ndc(code: str) -> str:
    """Strip non-digit characters and return up to 3 digits."""
    digits = re.sub(r"[^\d]", "", code)
    return digits[:3] if digits else ""
