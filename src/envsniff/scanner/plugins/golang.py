"""Go language scanner plugin using tree-sitter."""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language, Node, Parser
import tree_sitter_go as tsg

from envsniff.models import EnvVarFinding, SourceLocation
from envsniff.scanner.type_inferrer import infer_type


_LANGUAGE = Language(tsg.language())
_PARSER = Parser(_LANGUAGE)


def _extract_go_string(node: Node) -> str | None:
    """Extract the string content from a Go interpreted_string_literal node."""
    if node.type == "interpreted_string_literal":
        for child in node.children:
            if child.type == "interpreted_string_literal_content":
                return child.text.decode("utf-8") if child.text else None
    return None


def _is_os_getenv_or_lookup(selector_node: Node) -> bool:
    """Return True if selector_node is os.Getenv or os.LookupEnv."""
    if selector_node.type != "selector_expression":
        return False
    children = selector_node.children
    if len(children) < 3:
        return False
    obj = children[0]
    field = children[-1]
    return (
        obj.type == "identifier"
        and obj.text == b"os"
        and field.type == "field_identifier"
        and field.text in (b"Getenv", b"LookupEnv")
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
        language="go",
    )


class GoPlugin:
    """Scans Go source files for os.Getenv / os.LookupEnv usage."""

    @property
    def language(self) -> str:
        return "go"

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".go"})

    def scan(self, file: Path) -> list[EnvVarFinding]:
        """Scan a Go file for env var usage.

        Detects:
        - os.Getenv("VAR")
        - os.LookupEnv("VAR")

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
                    language="go",
                )

        return list(findings_map.values())

    def _try_extract(
        self, node: Node, file: Path, source_lines: list[bytes]
    ) -> EnvVarFinding | None:
        # Pattern: call_expression with selector_expression os.Getenv / os.LookupEnv
        if node.type != "call_expression":
            return None

        func_node = node.children[0]
        if not _is_os_getenv_or_lookup(func_node):
            return None

        # Get the argument_list
        arg_list = next((c for c in node.children if c.type == "argument_list"), None)
        if arg_list is None:
            return None

        # First real argument
        args = [c for c in arg_list.children if c.type not in ("(", ")", ",")]
        if not args:
            return None

        first_arg = args[0]
        var_name = _extract_go_string(first_arg)
        if var_name is None:
            return None

        return _make_finding(var_name, file, node, source_lines)
