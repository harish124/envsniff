"""Unit tests for src/envsniff/hooks/precommit.py.

TDD RED phase — all tests should FAIL before implementation exists.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# get_staged_files()
# ---------------------------------------------------------------------------


class TestGetStagedFiles:
    """Tests for get_staged_files() helper."""

    def test_returns_list_of_paths_from_git_output(self) -> None:
        """git output with two files → list of two Path objects."""
        from envsniff.hooks.precommit import get_staged_files

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "src/app.py\nlib/utils.py\n"

        with patch("subprocess.run", return_value=mock_result):
            result = get_staged_files()

        assert result == [Path("src/app.py"), Path("lib/utils.py")]

    def test_returns_empty_list_when_no_staged_files(self) -> None:
        """Empty git output → empty list."""
        from envsniff.hooks.precommit import get_staged_files

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = get_staged_files()

        assert result == []

    def test_returns_empty_list_when_output_is_only_whitespace(self) -> None:
        """Whitespace-only git output → empty list."""
        from envsniff.hooks.precommit import get_staged_files

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "   \n\n  "

        with patch("subprocess.run", return_value=mock_result):
            result = get_staged_files()

        assert result == []

    def test_filters_out_blank_lines_in_git_output(self) -> None:
        """git output with blank separators → only real paths returned."""
        from envsniff.hooks.precommit import get_staged_files

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "src/app.py\n\nlib/utils.py\n"

        with patch("subprocess.run", return_value=mock_result):
            result = get_staged_files()

        assert result == [Path("src/app.py"), Path("lib/utils.py")]

    def test_returns_empty_list_when_git_not_available(self) -> None:
        """FileNotFoundError from subprocess (no git) → empty list."""
        from envsniff.hooks.precommit import get_staged_files

        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            result = get_staged_files()

        assert result == []

    def test_returns_empty_list_when_subprocess_raises_oserror(self) -> None:
        """OSError from subprocess → empty list."""
        from envsniff.hooks.precommit import get_staged_files

        with patch("subprocess.run", side_effect=OSError("unexpected error")):
            result = get_staged_files()

        assert result == []

    def test_calls_git_diff_cached_name_only(self) -> None:
        """Verifies the correct git command is issued."""
        from envsniff.hooks.precommit import get_staged_files

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            get_staged_files()

        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "diff", "--cached", "--name-only"]

    def test_single_staged_file_returns_single_path(self) -> None:
        """Single file in output → list with one Path."""
        from envsniff.hooks.precommit import get_staged_files

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ".env.example\n"

        with patch("subprocess.run", return_value=mock_result):
            result = get_staged_files()

        assert result == [Path(".env.example")]


# ---------------------------------------------------------------------------
# run_precommit_check()
# ---------------------------------------------------------------------------


class TestRunPrecommitCheck:
    """Tests for run_precommit_check() function."""

    def test_returns_zero_when_no_new_undocumented_vars(self, tmp_path: Path) -> None:
        """No new vars → exit code 0."""
        from envsniff.hooks.precommit import run_precommit_check

        # Create a .env.example that documents all vars
        env_example = tmp_path / ".env.example"
        env_example.write_text("DATABASE_URL=\n")

        # Python file that uses only the documented var
        py_file = tmp_path / "app.py"
        py_file.write_text('import os\ndb = os.environ["DATABASE_URL"]\n')

        staged = [py_file]
        with patch("envsniff.hooks.precommit.get_staged_files", return_value=staged):
            result = run_precommit_check(tmp_path)

        assert result == 0

    def test_returns_one_when_new_undocumented_vars_found(self, tmp_path: Path) -> None:
        """New undocumented var → exit code 1."""
        from envsniff.hooks.precommit import run_precommit_check

        # No .env.example exists
        py_file = tmp_path / "app.py"
        py_file.write_text('import os\ntoken = os.getenv("SECRET_TOKEN")\n')

        staged = [py_file]
        with patch("envsniff.hooks.precommit.get_staged_files", return_value=staged):
            result = run_precommit_check(tmp_path)

        assert result == 1

    def test_returns_zero_when_no_staged_files_scanned(self, tmp_path: Path) -> None:
        """No staged Python/JS files → nothing to check → exit 0."""
        from envsniff.hooks.precommit import run_precommit_check

        staged: list[Path] = []
        with patch("envsniff.hooks.precommit.get_staged_files", return_value=staged):
            result = run_precommit_check(tmp_path)

        assert result == 0

    def test_falls_back_to_full_scan_when_git_unavailable(self, tmp_path: Path) -> None:
        """When git is not available, fall back to scanning repo_root entirely."""
        from envsniff.hooks.precommit import run_precommit_check

        # get_staged_files returns empty because git is unavailable
        # but there ARE vars in the repo_root — fallback should find them
        py_file = tmp_path / "main.py"
        py_file.write_text('import os\nval = os.getenv("FALLBACK_VAR")\n')

        # Simulate git not available: get_staged_files returns []
        with patch("envsniff.hooks.precommit.get_staged_files", return_value=[]):
            # With no staged files and no .env.example, full scan should find FALLBACK_VAR
            # but since we return [] for staged, the fallback scan of repo_root runs
            result = run_precommit_check(tmp_path)

        # Full-scan finds FALLBACK_VAR, no .env.example → exit 1
        assert result == 1

    def test_all_staged_vars_documented_returns_zero(self, tmp_path: Path) -> None:
        """All staged vars are already documented → exit 0."""
        from envsniff.hooks.precommit import run_precommit_check

        env_example = tmp_path / ".env.example"
        env_example.write_text("API_KEY=\nDB_HOST=\n")

        py_file = tmp_path / "service.py"
        py_file.write_text(
            'import os\napi_key = os.getenv("API_KEY")\nhost = os.environ["DB_HOST"]\n'
        )

        staged = [py_file]
        with patch("envsniff.hooks.precommit.get_staged_files", return_value=staged):
            result = run_precommit_check(tmp_path)

        assert result == 0

    def test_mixed_vars_some_new_returns_one(self, tmp_path: Path) -> None:
        """Some documented, some new → exit 1."""
        from envsniff.hooks.precommit import run_precommit_check

        env_example = tmp_path / ".env.example"
        env_example.write_text("KNOWN_VAR=\n")

        py_file = tmp_path / "app.py"
        py_file.write_text(
            'import os\n'
            'x = os.getenv("KNOWN_VAR")\n'
            'y = os.getenv("BRAND_NEW_VAR")\n'
        )

        staged = [py_file]
        with patch("envsniff.hooks.precommit.get_staged_files", return_value=staged):
            result = run_precommit_check(tmp_path)

        assert result == 1
