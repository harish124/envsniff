"""Unit tests for the npx-wrapper npm package.

Validates package.json structure and envsniff.js content without executing JS.

TDD RED phase — tests should FAIL before the files exist.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

# Root of the project (3 dirs up from this file: unit/hooks/test_npm_wrapper.py)
PROJECT_ROOT = Path(__file__).parents[3]
WRAPPER_DIR = PROJECT_ROOT / "npx-wrapper"
PACKAGE_JSON = WRAPPER_DIR / "package.json"
BIN_JS = WRAPPER_DIR / "bin" / "envsniff.js"


class TestPackageJson:
    """Validates the npx-wrapper/package.json structure."""

    def test_package_json_exists(self) -> None:
        """npx-wrapper/package.json must exist."""
        assert PACKAGE_JSON.exists(), f"Missing: {PACKAGE_JSON}"

    def test_package_json_is_valid_json(self) -> None:
        """package.json must be parseable JSON."""
        content = PACKAGE_JSON.read_text()
        data = json.loads(content)  # raises if invalid
        assert isinstance(data, dict)

    def test_package_json_has_name_field(self) -> None:
        """package.json must have a 'name' field."""
        data = json.loads(PACKAGE_JSON.read_text())
        assert "name" in data

    def test_package_json_name_is_envsniff(self) -> None:
        """package.json name must be 'envsniff'."""
        data = json.loads(PACKAGE_JSON.read_text())
        assert data["name"] == "envsniff"

    def test_package_json_has_version_field(self) -> None:
        """package.json must have a 'version' field."""
        data = json.loads(PACKAGE_JSON.read_text())
        assert "version" in data

    def test_package_json_has_bin_field(self) -> None:
        """package.json must have a 'bin' field."""
        data = json.loads(PACKAGE_JSON.read_text())
        assert "bin" in data

    def test_package_json_bin_points_to_envsniff_js(self) -> None:
        """bin.envsniff must point to ./bin/envsniff.js."""
        data = json.loads(PACKAGE_JSON.read_text())
        assert data["bin"]["envsniff"] == "./bin/envsniff.js"

    def test_package_json_has_description(self) -> None:
        """package.json must have a 'description' field."""
        data = json.loads(PACKAGE_JSON.read_text())
        assert "description" in data
        assert len(data["description"]) > 0

    def test_package_json_has_files_field(self) -> None:
        """package.json must include a 'files' field."""
        data = json.loads(PACKAGE_JSON.read_text())
        assert "files" in data

    def test_package_json_files_includes_bin(self) -> None:
        """files array must include 'bin/' directory."""
        data = json.loads(PACKAGE_JSON.read_text())
        assert "bin/" in data["files"]

    def test_package_json_has_engines_field(self) -> None:
        """package.json must specify node engine constraint."""
        data = json.loads(PACKAGE_JSON.read_text())
        assert "engines" in data
        assert "node" in data["engines"]


class TestEnvsniffJs:
    """Validates the content of npx-wrapper/bin/envsniff.js."""

    def test_envsniff_js_exists(self) -> None:
        """npx-wrapper/bin/envsniff.js must exist."""
        assert BIN_JS.exists(), f"Missing: {BIN_JS}"

    def test_envsniff_js_has_node_shebang(self) -> None:
        """File must start with #!/usr/bin/env node shebang."""
        content = BIN_JS.read_text()
        assert content.startswith("#!/usr/bin/env node"), (
            "envsniff.js must start with #!/usr/bin/env node"
        )

    def test_envsniff_js_contains_pipx_run_envsniff(self) -> None:
        """File must contain 'pipx run envsniff' as fallback."""
        content = BIN_JS.read_text()
        assert "pipx run envsniff" in content, (
            "envsniff.js must include 'pipx run envsniff' fallback"
        )

    def test_envsniff_js_contains_process_argv(self) -> None:
        """File must use process.argv to forward CLI arguments."""
        content = BIN_JS.read_text()
        assert "process.argv" in content, (
            "envsniff.js must reference process.argv"
        )

    def test_envsniff_js_contains_spawn_or_execsync(self) -> None:
        """File must use spawn or execSync for subprocess execution."""
        content = BIN_JS.read_text()
        has_spawn = "spawn" in content
        has_exec = "execSync" in content or "exec" in content
        assert has_spawn or has_exec, (
            "envsniff.js must use 'spawn' or 'execSync' for process execution"
        )

    def test_envsniff_js_contains_install_instructions_fallback(self) -> None:
        """File must print install instructions when envsniff not found."""
        content = BIN_JS.read_text()
        # Should mention pip or install somewhere as the last resort
        has_pip = "pip" in content
        has_install = "install" in content.lower()
        assert has_pip or has_install, (
            "envsniff.js must include install instructions as final fallback"
        )

    def test_envsniff_js_forwards_exit_code(self) -> None:
        """File must forward the child process exit code."""
        content = BIN_JS.read_text()
        assert "process.exit" in content, (
            "envsniff.js must call process.exit to forward exit code"
        )
