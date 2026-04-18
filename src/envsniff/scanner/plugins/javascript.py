"""JavaScript / TypeScript language scanner plugin using tree-sitter."""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language, Node, Parser
import tree_sitter_javascript as tsj

from envsniff.models import EnvVarFinding, SourceLocation
from envsniff.scanner.type_inferrer import infer_type


_LANGUAGE = Language(tsj.language())
_PARSER = Parser(_LANGUAGE)


def _extract_string_fragment(node: Node) -> str | None:
    """Extract string content from a JS string node."""
    if node.type == "string":
        for child in node.children:
            if child.type == "string_fragment":
                return child.text.decode("utf-8") if child.text else None
    return None


def _is_process_env(node: Node) -> bool:
    """Return True if node is the member_expression `process.env`."""
    if node.type != "member_expression":
        return False
    children = node.children
    if len(children) < 3:
        return False
    obj = children[0]
    prop = children[-1]
    return (
        obj.type == "identifier"
        and obj.text == b"process"
        and prop.type == "property_identifier"
        and prop.text == b"env"
    )


def _walk(node: Node) -> list[Node]:
    """Walk all descendants in pre-order."""
    result: list[Node] = []
    stack = [node]
    while stack:
        current = stack.pop()
        result.append(current)
        stack.extend(reversed(current.children))
    return result


def _make_finding(
    name: str,
    file: Path,
    node: Node,
    source_lines: list[bytes],
) -> EnvVarFinding:
    line_num = node.start_point[0]
    col = node.start_point[1]
    snippet = source_lines[line_num].decode("utf-8", errors="replace").rstrip()
    location = SourceLocation(file=file, line=line_num + 1, column=col, snippet=snippet)
    return EnvVarFinding(
        name=name,
        locations=(location,),
        default_value=None,
        inferred_type=infer_type(name),
        is_required=True,
        language="javascript",
    )


class JavaScriptPlugin:
    """Scans JavaScript and TypeScript files for process.env usage."""

    @property
    def language(self) -> str:
        return "javascript"

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"})

    def scan(self, file: Path) -> list[EnvVarFinding]:
        """Scan a JS/TS file for process.env patterns.

        Detects:
        - process.env.VAR
        - process.env["VAR"]

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

        source_lines = source.split(b"\n")

        try:
            tree = _PARSER.parse(source)
        except Exception:
            return []

        findings_map: dict[str, EnvVarFinding] = {}

        for node in _walk(tree.root_node):
            finding = self._try_extract(node, file, source_lines)
            if finding is None:
                continue
            name = finding.name
            if name not in findings_map:
                findings_map[name] = finding
            else:
                existing = findings_map[name]
                findings_map[name] = EnvVarFinding(
                    name=name,
                    locations=existing.locations + finding.locations,
                    default_value=existing.default_value,
                    inferred_type=existing.inferred_type,
                    is_required=existing.is_required,
                    language="javascript",
                )

        return list(findings_map.values())

    def _try_extract(
        self, node: Node, file: Path, source_lines: list[bytes]
    ) -> EnvVarFinding | None:
        # Pattern 1: process.env.VAR (nested member_expression)
        if node.type == "member_expression":
            children = node.children
            if len(children) < 3:
                return None
            obj = children[0]
            prop = children[-1]
            if _is_process_env(obj) and prop.type == "property_identifier":
                name = prop.text.decode("utf-8") if prop.text else None
                if name:
                    return _make_finding(name, file, node, source_lines)

        # Pattern 2: process.env["VAR"] (subscript_expression)
        if node.type == "subscript_expression":
            children = node.children
            if len(children) < 3:
                return None
            obj = children[0]
            # key is between [ and ]
            key_nodes = [c for c in children if c.type not in ("member_expression", "[", "]")]
            if not key_nodes:
                return None
            if _is_process_env(obj):
                key_node = key_nodes[0]
                name = _extract_string_fragment(key_node)
                if name:
                    return _make_finding(name, file, node, source_lines)

        return None
