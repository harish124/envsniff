"""Type inference for environment variable names.

Reuses the :class:`~envsniff.models.InferredType` enum already defined in
``models.py``.  This module provides a public function ``infer_type_from_name``
that classifies variable names using suffix/prefix pattern matching.

Patterns (ordered most-specific first):
  - ``*_URL``, ``*_URI``  → URL
  - ``*_KEY``, ``*_TOKEN``, ``*_SECRET``, ``*_PASSWORD``  → SECRET
  - ``*_PORT``, ``PORT``  → INTEGER
  - ``*_HOST``, ``HOST``  → STRING
  - ``DEBUG``, ``VERBOSE``, ``*_ENABLED``, ``*_DISABLED``, ``*_FLAG``  → BOOLEAN
  - Everything else  → STRING
"""

from __future__ import annotations

from envsniff.models import InferredType

# Ordered list of (suffixes_or_exact_names, InferredType).
# Each entry is checked in order; the first match wins.
_PATTERNS: list[tuple[tuple[str, ...], InferredType]] = [
    # URL / URI
    (("_URL", "_URI"), InferredType.URL),
    # Secrets — checked before PORT so *_KEY matches SECRET not STRING
    (("_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "_PASSWD", "_PASS", "_PRIVATE"), InferredType.SECRET),
    # Port — integer type
    (("_PORT", "PORT"), InferredType.INTEGER),
    # Host — string type (explicit, for clarity)
    (("_HOST", "HOST"), InferredType.STRING),
    # Boolean flags
    (("DEBUG", "VERBOSE", "_ENABLED", "_DISABLED", "_FLAG", "_ACTIVE"), InferredType.BOOLEAN),
]


def infer_type_from_name(name: str) -> InferredType:
    """Infer the semantic type of an environment variable from its *name*.

    Args:
        name: Environment variable name (any case).

    Returns:
        The most specific :class:`~envsniff.models.InferredType` that matches
        the name, or :attr:`~envsniff.models.InferredType.STRING` as a fallback.
    """
    upper = name.upper()

    for suffixes, inferred_type in _PATTERNS:
        for pattern in suffixes:
            # Exact match (e.g. "PORT", "DEBUG")
            if upper == pattern.lstrip("_"):
                return inferred_type
            # Suffix match (e.g. "SERVER_PORT", "DATABASE_URL")
            if pattern.startswith("_") and upper.endswith(pattern):
                return inferred_type

    return InferredType.STRING
