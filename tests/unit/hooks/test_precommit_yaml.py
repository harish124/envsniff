"""Unit tests for .pre-commit-hooks.yaml structure.

Validates the pre-commit hook configuration file at the project root.

TDD RED phase — tests should FAIL before the file exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml  # type: ignore[import]

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

PROJECT_ROOT = Path(__file__).parents[3]
PRECOMMIT_HOOKS_YAML = PROJECT_ROOT / ".pre-commit-hooks.yaml"


def _load_yaml() -> list[dict]:  # type: ignore[type-arg]
    """Load and parse the pre-commit-hooks.yaml file using simple parsing."""
    if HAS_YAML:
        import yaml

        content = PRECOMMIT_HOOKS_YAML.read_text()
        return yaml.safe_load(content)  # type: ignore[no-any-return]
    else:
        # Minimal fallback: parse enough to run the tests without pyyaml
        import re

        content = PRECOMMIT_HOOKS_YAML.read_text()
        # Use regex to extract key fields from the YAML.
        # Lines may start with "- " (list item) or be plain "key: value".
        hook: dict[str, object] = {}  # type: ignore[type-arg]
        for line in content.splitlines():
            stripped = line.strip().lstrip("- ")
            for key in ("id", "name", "entry", "language", "pass_filenames", "always_run"):
                m = re.match(rf"^{key}:\s*(.+)$", stripped)
                if m:
                    val: object = m.group(1).strip()
                    if val == "true":
                        val = True
                    elif val == "false":
                        val = False
                    hook[key] = val
        return [hook]


class TestPrecommitHooksYaml:
    """Validates .pre-commit-hooks.yaml at the project root."""

    def test_file_exists(self) -> None:
        """.pre-commit-hooks.yaml must exist at project root."""
        assert PRECOMMIT_HOOKS_YAML.exists(), f"Missing: {PRECOMMIT_HOOKS_YAML}"

    def test_file_is_not_empty(self) -> None:
        """File must have non-empty content."""
        assert PRECOMMIT_HOOKS_YAML.stat().st_size > 0

    def test_contains_envsniff_check_hook(self) -> None:
        """Must define a hook with id 'envsniff-check'."""
        hooks = _load_yaml()
        ids = [h.get("id") for h in hooks]
        assert "envsniff-check" in ids, f"Expected 'envsniff-check' hook id, got: {ids}"

    def test_hook_language_is_python(self) -> None:
        """Hook language must be 'python'."""
        hooks = _load_yaml()
        hook = next(h for h in hooks if h.get("id") == "envsniff-check")
        assert hook.get("language") == "python"

    def test_hook_pass_filenames_is_false(self) -> None:
        """pass_filenames must be false (envsniff scans the whole repo)."""
        hooks = _load_yaml()
        hook = next(h for h in hooks if h.get("id") == "envsniff-check")
        assert hook.get("pass_filenames") is False

    def test_hook_entry_is_envsniff_check(self) -> None:
        """entry must invoke 'envsniff check'."""
        hooks = _load_yaml()
        hook = next(h for h in hooks if h.get("id") == "envsniff-check")
        entry = str(hook.get("entry", ""))
        assert "envsniff" in entry and "check" in entry, (
            f"Hook entry should be 'envsniff check', got: {entry!r}"
        )

    def test_hook_has_name_field(self) -> None:
        """Hook must have a human-readable 'name' field."""
        hooks = _load_yaml()
        hook = next(h for h in hooks if h.get("id") == "envsniff-check")
        assert "name" in hook
        assert len(str(hook["name"])) > 0
