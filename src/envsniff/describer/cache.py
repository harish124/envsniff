"""Description cache for the AI describer.

Cache entries are stored in a JSON file at ``~/.cache/envsniff/descriptions.json``
(or any path provided at construction time).

Cache key formula::

    sha256(var_name + ":" + ":".join(sorted(snippets)) + ":" + (default_value or ""))
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def make_cache_key(
    var_name: str,
    snippets: list[str],
    default_value: str | None,
) -> str:
    """Compute a stable SHA-256 cache key for a variable description request.

    Args:
        var_name: The environment variable name.
        snippets: Source-code snippets where the variable was found.
            Sorted before hashing so order does not matter.
        default_value: The default value (if any); ``None`` and ``""`` produce
            different keys deliberately.

    Returns:
        64-character lowercase hexadecimal SHA-256 digest.
    """
    sorted_snippets = sorted(snippets)
    dv_part = default_value if default_value is not None else "\x00none\x00"
    raw = var_name + ":" + ":".join(sorted_snippets) + ":" + dv_part
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class DescriptionCache:
    """Persistent JSON cache for ``(description, example_value)`` tuples.

    Args:
        cache_path: Path to the JSON cache file.  Defaults to
            ``~/.cache/envsniff/descriptions.json``.
    """

    def __init__(self, cache_path: Path | None = None) -> None:
        if cache_path is None:
            cache_path = Path.home() / ".cache" / "envsniff" / "descriptions.json"
        self.cache_path = cache_path
        self._data: dict[str, tuple[str, str]] | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, tuple[str, str]]:
        """Load cache from disk, returning an empty dict on any error."""
        if not self.cache_path.exists():
            return {}
        try:
            raw: dict[str, list[str]] = json.loads(self.cache_path.read_text(encoding="utf-8"))
            # Stored as lists for JSON compatibility; convert back to tuples.
            return {k: (v[0], v[1]) for k, v in raw.items() if isinstance(v, list) and len(v) == 2}
        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            return {}

    def _ensure_loaded(self) -> dict[str, tuple[str, str]]:
        if self._data is None:
            self._data = self._load()
        return self._data

    def _save(self) -> None:
        """Persist in-memory cache to disk."""
        data = self._ensure_loaded()
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> tuple[str, str] | None:
        """Return the cached ``(description, example)`` for *key*, or ``None``."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = self._ensure_loaded()
        return data.get(key)

    def set(self, key: str, value: tuple[str, str]) -> None:
        """Store *value* under *key* and persist to disk.

        Args:
            key: Cache key (typically from :func:`make_cache_key`).
            value: ``(description, example_value)`` tuple.
        """
        data = self._ensure_loaded()
        data[key] = value
        self._save()
