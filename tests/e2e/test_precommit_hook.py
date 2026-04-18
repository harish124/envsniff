"""E2E tests for the pre-commit hook integration.

Uses a real temporary git repository to validate end-to-end behavior
of run_precommit_check().

TDD RED phase — tests should FAIL before implementation exists.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


def _init_git_repo(path: Path) -> None:
    """Initialise a git repo at path (best-effort, tolerate missing git)."""
    try:
        subprocess.run(
            ["git", "init", str(path)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(path), "config", "user.email", "test@test.com"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(path), "config", "user.name", "Test"],
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass  # git not available; tests that need it will be skipped


def _stage_file(repo: Path, file_path: Path) -> None:
    """Add a file to the git index (best-effort)."""
    try:
        subprocess.run(
            ["git", "-C", str(repo), "add", str(file_path)],
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository."""
    _init_git_repo(tmp_path)
    return tmp_path


class TestPrecommitHookE2E:
    """End-to-end tests using a real temporary git repository."""

    def test_returns_one_when_no_env_example_and_new_var_staged(
        self, git_repo: Path
    ) -> None:
        """Staging a file with an undocumented env var and no .env.example → exit 1."""
        from envsniff.hooks.precommit import run_precommit_check

        py_file = git_repo / "app.py"
        py_file.write_text('import os\ntoken = os.getenv("NEW_UNDOCUMENTED_VAR")\n')
        _stage_file(git_repo, py_file)

        staged_files = [py_file]
        with patch("envsniff.hooks.precommit.get_staged_files", return_value=staged_files):
            result = run_precommit_check(git_repo)

        assert result == 1

    def test_returns_zero_when_env_example_documents_the_var(
        self, git_repo: Path
    ) -> None:
        """.env.example documents the var used in staged file → exit 0."""
        from envsniff.hooks.precommit import run_precommit_check

        env_example = git_repo / ".env.example"
        env_example.write_text("NEW_DOCUMENTED_VAR=\n")

        py_file = git_repo / "app.py"
        py_file.write_text('import os\ntoken = os.getenv("NEW_DOCUMENTED_VAR")\n')
        _stage_file(git_repo, py_file)

        staged_files = [py_file]
        with patch("envsniff.hooks.precommit.get_staged_files", return_value=staged_files):
            result = run_precommit_check(git_repo)

        assert result == 0

    def test_returns_zero_for_empty_staged_file_list(self, git_repo: Path) -> None:
        """No staged files → nothing scanned → exit 0."""
        from envsniff.hooks.precommit import run_precommit_check

        with patch("envsniff.hooks.precommit.get_staged_files", return_value=[]):
            result = run_precommit_check(git_repo)

        assert result == 0

    def test_returns_one_for_multiple_undocumented_vars(self, git_repo: Path) -> None:
        """Multiple new undocumented vars → exit 1."""
        from envsniff.hooks.precommit import run_precommit_check

        py_file = git_repo / "service.py"
        py_file.write_text(
            'import os\n'
            'db = os.getenv("DB_URL")\n'
            'key = os.getenv("API_KEY")\n'
        )
        _stage_file(git_repo, py_file)

        staged_files = [py_file]
        with patch("envsniff.hooks.precommit.get_staged_files", return_value=staged_files):
            result = run_precommit_check(git_repo)

        assert result == 1

    def test_partial_documentation_returns_one(self, git_repo: Path) -> None:
        """Only some vars documented → still exit 1 for the undocumented ones."""
        from envsniff.hooks.precommit import run_precommit_check

        env_example = git_repo / ".env.example"
        env_example.write_text("KNOWN_VAR=\n")

        py_file = git_repo / "app.py"
        py_file.write_text(
            'import os\n'
            'x = os.getenv("KNOWN_VAR")\n'
            'y = os.getenv("UNKNOWN_VAR")\n'
        )
        _stage_file(git_repo, py_file)

        staged_files = [py_file]
        with patch("envsniff.hooks.precommit.get_staged_files", return_value=staged_files):
            result = run_precommit_check(git_repo)

        assert result == 1

    def test_non_python_files_in_staged_list_handled_gracefully(
        self, git_repo: Path
    ) -> None:
        """Staged list containing non-scannable files → no crash → exit 0 if clean."""
        from envsniff.hooks.precommit import run_precommit_check

        # A README — not a scannable file
        readme = git_repo / "README.md"
        readme.write_text("# My project\n")
        _stage_file(git_repo, readme)

        staged_files = [readme]
        with patch("envsniff.hooks.precommit.get_staged_files", return_value=staged_files):
            result = run_precommit_check(git_repo)

        # No env vars found → clean
        assert result == 0
