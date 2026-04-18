"""Python language scanner plugin using tree-sitter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import tree_sitter_python as tsp
from tree_sitter import Language, Node, Parser

from envsniff.models import EnvVarFinding, SourceLocation
from envsniff.scanner.type_inferrer import infer_type

if TYPE_CHECKING:
    from pathlib import Path

_LANGUAGE = Language(tsp.language())
_PARSER = Parser(_LANGUAGE)


def _extract_string_value(node: Node) -> str | None:
    """Extract the string content from a tree-sitter string node."""
    if node.type == "string":
        for child in node.children:
            if child.type == "string_content":
                return child.text.decode("utf-8") if child.text else None
    return None


def _is_os_getenv_call(func_node: Node) -> bool:
    """Return True if func_node represents os.getenv."""
    if func_node.type != "attribute":
        return False
    children = func_node.children
    if len(children) < 3:
        return False
    obj = children[0]
    method = children[-1]
    return (
        obj.type == "identifier"
        and obj.text == b"os"
        and method.type == "identifier"
        and method.text == b"getenv"
    )


def _is_os_environ_get_call(func_node: Node) -> bool:
    """Return True if func_node represents os.environ.get."""
    if func_node.type != "attribute":
        return False
    # os.environ.get: attribute(attribute(os, environ), get)
    children = func_node.children
    if len(children) < 3:
        return False
    inner = children[0]
    method = children[-1]
    if method.type != "identifier" or method.text != b"get":
        return False
    if inner.type != "attribute":
        return False
    inner_children = inner.children
    if len(inner_children) < 3:
        return False
    return (
        inner_children[0].type == "identifier"
        and inner_children[0].text == b"os"
        and inner_children[-1].type == "identifier"
        and inner_children[-1].text == b"environ"
    )


def _is_os_environ_subscript(node: Node) -> bool:
    """Return True if node is os.environ[...]."""
    if node.type != "subscript":
        return False
    obj = node.children[0]
    if obj.type != "attribute":
        return False
    attr_children = obj.children
    if len(attr_children) < 3:
        return False
    return (
        attr_children[0].type == "identifier"
        and attr_children[0].text == b"os"
        and attr_children[-1].type == "identifier"
        and attr_children[-1].text == b"environ"
    )


def _get_call_args(arg_list_node: Node) -> list[Node]:
    """Return the argument nodes from an argument_list node."""
    return [child for child in arg_list_node.children if child.type not in ("(", ")", ",", "comment")]


def _make_finding(
    name: str,
    default_value: str | None,
    is_required: bool,
    file: Path,
    node: Node,
    source_lines: list[bytes],
) -> EnvVarFinding:
    """Create an EnvVarFinding from parsed data."""
    line_num = node.start_point[0]
    col = node.start_point[1]
    snippet = source_lines[line_num].decode("utf-8", errors="replace").rstrip()
    location = SourceLocation(file=file, line=line_num + 1, column=col, snippet=snippet)
    return EnvVarFinding(
        name=name,
        locations=(location,),
        default_value=default_value,
        inferred_type=infer_type(name),
        is_required=is_required,
        language="python",
    )


def _walk(node: Node) -> list[Node]:
    """Walk all descendants of a node, returning them in pre-order."""
    result: list[Node] = []
    stack = [node]
    while stack:
        current = stack.pop()
        result.append(current)
        stack.extend(reversed(current.children))
    return result


class PythonPlugin:
    """Scans Python source files for os.environ usage patterns."""

    @property
    def language(self) -> str:
        return "python"

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".py", ".pyw"})

    def scan(self, file: Path) -> list[EnvVarFinding]:
        """Scan a Python file for env var usage.

        Detects:
        - os.getenv("VAR") / os.getenv("VAR", "default")
        - os.environ.get("VAR") / os.environ.get("VAR", "default")
        - os.environ["VAR"]

        Returns:
            Deduplicated list of EnvVarFinding, one per unique var name.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")

        try:
            source = file.read_bytes()
        except (OSError, PermissionError):
            return []

        # Handle binary / non-UTF-8 files gracefully
        try:
            source_lines = source.split(b"\n")
        except Exception:
            return []

        try:
            tree = _PARSER.parse(source)
        except Exception:
            return []

        # Map of name → finding (for deduplication within file)
        findings_map: dict[str, EnvVarFinding] = {}

        for node in _walk(tree.root_node):
            finding = self._try_extract(node, file, source_lines)
            if finding is None:
                continue
            name = finding.name
            if name in findings_map:
                # Merge: combine locations, keep is_required=True if any usage lacks default
                existing = findings_map[name]
                merged_locations = existing.locations + finding.locations
                merged_required = existing.is_required or finding.is_required
                merged_default = existing.default_value or finding.default_value
                findings_map[name] = EnvVarFinding(
                    name=name,
                    locations=merged_locations,
                    default_value=merged_default,
                    inferred_type=existing.inferred_type,
                    is_required=merged_required,
                    language="python",
                )
            else:
                findings_map[name] = finding

        return list(findings_map.values())

    def _try_extract(
        self, node: Node, file: Path, source_lines: list[bytes]
    ) -> EnvVarFinding | None:
        """Try to extract an env var finding from a single node.

        Returns None if the node doesn't match any known pattern.
        """
        # Pattern: os.getenv("VAR") or os.getenv("VAR", "default")
        if node.type == "call":
            func_children = [c for c in node.children if c.type not in ("(", ")")]
            if not func_children:
                return None
            func_node = node.children[0]
            arg_list = next((c for c in node.children if c.type == "argument_list"), None)
            if arg_list is None:
                return None
            args = _get_call_args(arg_list)
            if not args:
                return None

            # os.getenv("VAR", "default")
            if _is_os_getenv_call(func_node):
                first_arg = args[0]
                var_name = _extract_string_value(first_arg)
                if var_name is None:
                    return None  # Dynamic key — skip
                default_value = _extract_string_value(args[1]) if len(args) >= 2 else None
                is_required = default_value is None and len(args) < 2
                return _make_finding(var_name, default_value, is_required, file, node, source_lines)

            # os.environ.get("VAR", "default")
            if _is_os_environ_get_call(func_node):
                first_arg = args[0]
                var_name = _extract_string_value(first_arg)
                if var_name is None:
                    return None
                default_value = _extract_string_value(args[1]) if len(args) >= 2 else None
                is_required = default_value is None and len(args) < 2
                return _make_finding(var_name, default_value, is_required, file, node, source_lines)

        # Pattern: os.environ["VAR"]
        if node.type == "subscript" and _is_os_environ_subscript(node):
            # The subscript key is the second meaningful child (after [ )
            key_candidates = [
                c for c in node.children if c.type not in ("attribute", "[", "]")
            ]
            if not key_candidates:
                return None
            key_node = key_candidates[0]
            var_name = _extract_string_value(key_node)
            if var_name is None:
                return None
            return _make_finding(var_name, None, True, file, node, source_lines)

        return None
