"""Infer the type of an environment variable from its name."""

from __future__ import annotations

from envsniff.models import InferredType

# Suffix/prefix patterns ordered from most to least specific
_PATTERNS: list[tuple[tuple[str, ...], InferredType]] = [
    # URL / URI
    (("_URL", "_URI", "_DSN", "_ENDPOINT"), InferredType.URL),
    # Secrets
    (("_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "_PASSWD", "_PASS", "_CREDENTIALS", "_CERT", "_PRIVATE"), InferredType.SECRET),
    # Port
    (("_PORT",), InferredType.PORT),
    # Boolean flags
    (("DEBUG", "VERBOSE", "_ENABLED", "_DISABLED", "_FLAG", "_ACTIVE"), InferredType.BOOLEAN),
    # Integer
    (("_PORT", "_TIMEOUT", "_RETRIES", "_MAX", "_MIN", "_COUNT", "_SIZE", "_LIMIT", "_TTL", "_INTERVAL"), InferredType.INTEGER),
]

# Exact name matches take priority
_EXACT: dict[str, InferredType] = {
    "DEBUG": InferredType.BOOLEAN,
    "VERBOSE": InferredType.BOOLEAN,
    "PORT": InferredType.PORT,
}


def infer_type(name: str) -> InferredType:
    """Infer the semantic type of an environment variable from its name.

    Args:
        name: The environment variable name (UPPER_SNAKE_CASE expected).

    Returns:
        The most likely InferredType based on name patterns.
    """
    upper = name.upper()

    # Exact match first
    if upper in _EXACT:
        return _EXACT[upper]

    # Suffix/prefix pattern matching (most specific first)
    for suffixes, inferred in _PATTERNS:
        for suffix in suffixes:
            if upper.endswith(suffix) or upper == suffix.lstrip("_"):
                return inferred

    return InferredType.STRING
