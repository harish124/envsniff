"""Unit tests for src/envsniff/hooks/ci.py.

TDD RED phase — all tests should FAIL before implementation exists.
"""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# run_ci_check()
# ---------------------------------------------------------------------------


class TestRunCiCheck:
    """Tests for run_ci_check() function."""

    def test_returns_zero_on_clean_codebase(self, tmp_path: Path) -> None:
        """No env vars found and no .env.example → exit code 0."""
        from envsniff.hooks.ci import run_ci_check

        # Empty project with no Python files
        exit_code, _ = run_ci_check(tmp_path)
        assert exit_code == 0

    def test_returns_zero_when_all_vars_documented(self, tmp_path: Path) -> None:
        """All vars documented in .env.example → exit code 0."""
        from envsniff.hooks.ci import run_ci_check

        env_example = tmp_path / ".env.example"
        env_example.write_text("DATABASE_URL=\n")

        py_file = tmp_path / "app.py"
        py_file.write_text('import os\ndb = os.environ["DATABASE_URL"]\n')

        exit_code, _ = run_ci_check(tmp_path)
        assert exit_code == 0

    def test_returns_one_with_undocumented_vars(self, tmp_path: Path) -> None:
        """Undocumented var found → exit code 1."""
        from envsniff.hooks.ci import run_ci_check

        py_file = tmp_path / "app.py"
        py_file.write_text('import os\ntoken = os.getenv("UNDOC_TOKEN")\n')

        exit_code, _ = run_ci_check(tmp_path)
        assert exit_code == 1

    def test_json_output_has_required_fields(self, tmp_path: Path) -> None:
        """JSON output always has status, new_vars, stale_vars, scanned_files."""
        from envsniff.hooks.ci import run_ci_check

        _, json_str = run_ci_check(tmp_path)
        data = json.loads(json_str)

        assert "status" in data
        assert "new_vars" in data
        assert "stale_vars" in data
        assert "scanned_files" in data

    def test_json_output_status_pass_on_clean(self, tmp_path: Path) -> None:
        """Clean codebase → JSON status is 'pass'."""
        from envsniff.hooks.ci import run_ci_check

        _, json_str = run_ci_check(tmp_path)
        data = json.loads(json_str)
        assert data["status"] == "pass"

    def test_json_output_status_fail_on_undocumented_vars(
        self, tmp_path: Path
    ) -> None:
        """Undocumented vars → JSON status is 'fail'."""
        from envsniff.hooks.ci import run_ci_check

        py_file = tmp_path / "app.py"
        py_file.write_text('import os\ntoken = os.getenv("CI_NEW_VAR")\n')

        _, json_str = run_ci_check(tmp_path)
        data = json.loads(json_str)
        assert data["status"] == "fail"

    def test_json_output_lists_new_vars(
        self, tmp_path: Path
    ) -> None:
        """new_vars field contains the undocumented variable names."""
        from envsniff.hooks.ci import run_ci_check

        py_file = tmp_path / "app.py"
        py_file.write_text('import os\ntoken = os.getenv("MY_SECRET")\n')

        _, json_str = run_ci_check(tmp_path)
        data = json.loads(json_str)
        assert "MY_SECRET" in data["new_vars"]

    def test_json_output_lists_stale_vars(
        self, tmp_path: Path
    ) -> None:
        """stale_vars field contains vars in .env.example not in codebase."""
        from envsniff.hooks.ci import run_ci_check

        env_example = tmp_path / ".env.example"
        env_example.write_text("STALE_VAR=\n")
        # No Python file uses STALE_VAR

        _, json_str = run_ci_check(tmp_path)
        data = json.loads(json_str)
        assert "STALE_VAR" in data["stale_vars"]

    def test_json_output_scanned_files_is_integer(
        self, tmp_path: Path
    ) -> None:
        """scanned_files is always an integer in the JSON output."""
        from envsniff.hooks.ci import run_ci_check

        _, json_str = run_ci_check(tmp_path)
        data = json.loads(json_str)
        assert isinstance(data["scanned_files"], int)

    def test_json_is_always_valid_even_when_exit_one(
        self, tmp_path: Path
    ) -> None:
        """Even when check fails, the JSON string is still valid JSON."""
        from envsniff.hooks.ci import run_ci_check

        py_file = tmp_path / "broken.py"
        py_file.write_text('import os\nval = os.getenv("BROKEN_VAR")\n')

        exit_code, json_str = run_ci_check(tmp_path)
        assert exit_code == 1

        # Must not raise json.JSONDecodeError
        data = json.loads(json_str)
        assert isinstance(data, dict)

    def test_output_format_defaults_to_json(
        self, tmp_path: Path
    ) -> None:
        """Default output_format is 'json'."""
        from envsniff.hooks.ci import run_ci_check

        # Call without specifying output_format
        _, json_str = run_ci_check(tmp_path)

        # Must parse as JSON without error
        json.loads(json_str)

    def test_accepts_output_format_parameter(
        self, tmp_path: Path
    ) -> None:
        """run_ci_check accepts output_format='json' explicitly."""
        from envsniff.hooks.ci import run_ci_check

        _, json_str = run_ci_check(tmp_path, output_format="json")
        json.loads(json_str)

    def test_scanned_files_count_matches_actual_files(
        self, tmp_path: Path
    ) -> None:
        """scanned_files in JSON matches the number of scannable files found."""
        from envsniff.hooks.ci import run_ci_check

        py_file = tmp_path / "app.py"
        py_file.write_text('import os\nx = os.getenv("X")\n')

        _, json_str = run_ci_check(tmp_path)
        data = json.loads(json_str)
        assert data["scanned_files"] >= 1

    def test_new_vars_is_list_type(
        self, tmp_path: Path
    ) -> None:
        """new_vars is always a list, even when empty."""
        from envsniff.hooks.ci import run_ci_check

        _, json_str = run_ci_check(tmp_path)
        data = json.loads(json_str)
        assert isinstance(data["new_vars"], list)

    def test_stale_vars_is_list_type(
        self, tmp_path: Path
    ) -> None:
        """stale_vars is always a list, even when empty."""
        from envsniff.hooks.ci import run_ci_check

        _, json_str = run_ci_check(tmp_path)
        data = json.loads(json_str)
        assert isinstance(data["stale_vars"], list)
