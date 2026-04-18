"""Protocol definition for language scanner plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from tree_sitter import Node

    from envsniff.models import EnvVarFinding


@runtime_checkable
class LanguageScanner(Protocol):
    """Protocol that all language scanner plugins must implement."""

    @property
    def language(self) -> str:
        """Return the language name (e.g. 'python', 'javascript')."""
        ...

    @property
    def supported_extensions(self) -> frozenset[str]:
        """Return the file extensions handled by this plugin (e.g. {'.py'})."""
        ...

    def scan(self, file: Path) -> list[EnvVarFinding]:
        """Scan a single file and return all env var findings."""
        ...


def walk_tree(node: Node) -> list[Node]:
    """Walk all descendants of a node, returning them in pre-order.

    This shared utility is used by Python, JavaScript, and Go plugins to
    traverse tree-sitter parse trees without duplicating the walk logic.

    Args:
        node: The root node to walk from.

    Returns:
        All nodes in pre-order traversal (root first, then children).
    """
    result: list[Node] = []
    stack = [node]
    while stack:
        current = stack.pop()
        result.append(current)
        stack.extend(reversed(current.children))
    return result
