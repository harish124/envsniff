"""Unit tests for GitHub Actions workflow files.

Validates .github/workflows/ci.yml and .github/workflows/publish.yml structure.

TDD RED phase — tests should FAIL before the files exist.
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml  # type: ignore[import]

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

PROJECT_ROOT = Path(__file__).parents[2]
CI_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
PUBLISH_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "publish.yml"


def _load_yaml_file(path: Path) -> dict:  # type: ignore[type-arg]
    """Load a YAML workflow file."""
    if HAS_YAML:
        import yaml

        return yaml.safe_load(path.read_text())  # type: ignore[no-any-return]
    else:
        # Minimal content-based checks via raw text when pyyaml not available
        return {"_raw": path.read_text()}


class TestCiWorkflow:
    """Validates .github/workflows/ci.yml."""

    def test_ci_yml_exists(self) -> None:
        """.github/workflows/ci.yml must exist."""
        assert CI_WORKFLOW.exists(), f"Missing: {CI_WORKFLOW}"

    def test_ci_yml_is_not_empty(self) -> None:
        """ci.yml must have non-empty content."""
        assert CI_WORKFLOW.stat().st_size > 0

    def test_ci_yml_runs_pytest(self) -> None:
        """ci.yml must invoke pytest."""
        content = CI_WORKFLOW.read_text()
        assert "pytest" in content, "ci.yml must run pytest"

    def test_ci_yml_runs_ruff(self) -> None:
        """ci.yml must invoke ruff for linting."""
        content = CI_WORKFLOW.read_text()
        assert "ruff" in content, "ci.yml must run ruff check"

    def test_ci_yml_has_python_matrix(self) -> None:
        """ci.yml must test against a matrix of Python versions."""
        content = CI_WORKFLOW.read_text()
        assert "matrix" in content, "ci.yml must use a version matrix"

    def test_ci_yml_includes_python_311(self) -> None:
        """Matrix must include Python 3.11."""
        content = CI_WORKFLOW.read_text()
        assert "3.11" in content, "ci.yml matrix must include Python 3.11"

    def test_ci_yml_includes_python_312(self) -> None:
        """Matrix must include Python 3.12."""
        content = CI_WORKFLOW.read_text()
        assert "3.12" in content, "ci.yml matrix must include Python 3.12"

    def test_ci_yml_includes_python_313(self) -> None:
        """Matrix must include Python 3.13."""
        content = CI_WORKFLOW.read_text()
        assert "3.13" in content, "ci.yml matrix must include Python 3.13"

    def test_ci_yml_triggers_on_push(self) -> None:
        """ci.yml must trigger on push events."""
        content = CI_WORKFLOW.read_text()
        assert "push" in content, "ci.yml must trigger on push"

    def test_ci_yml_triggers_on_pull_request(self) -> None:
        """ci.yml must trigger on pull_request events."""
        content = CI_WORKFLOW.read_text()
        assert "pull_request" in content, "ci.yml must trigger on pull_request"

    def test_ci_yml_uses_poetry(self) -> None:
        """ci.yml must use poetry for dependency management."""
        content = CI_WORKFLOW.read_text()
        assert "poetry" in content, "ci.yml must use poetry"

    def test_ci_yml_installs_dev_dependencies(self) -> None:
        """ci.yml must install dev dependencies."""
        content = CI_WORKFLOW.read_text()
        assert "poetry install" in content or "poetry run" in content

    def test_ci_yml_runs_on_ubuntu(self) -> None:
        """ci.yml must run on ubuntu-latest."""
        content = CI_WORKFLOW.read_text()
        assert "ubuntu" in content, "ci.yml must run on ubuntu"


class TestPublishWorkflow:
    """Validates .github/workflows/publish.yml."""

    def test_publish_yml_exists(self) -> None:
        """.github/workflows/publish.yml must exist."""
        assert PUBLISH_WORKFLOW.exists(), f"Missing: {PUBLISH_WORKFLOW}"

    def test_publish_yml_is_not_empty(self) -> None:
        """publish.yml must have non-empty content."""
        assert PUBLISH_WORKFLOW.stat().st_size > 0

    def test_publish_yml_triggers_on_version_tags(self) -> None:
        """publish.yml must trigger on version tags matching v*."""
        content = PUBLISH_WORKFLOW.read_text()
        assert "tags" in content, "publish.yml must trigger on tags"
        assert "v*" in content or "v" in content, "publish.yml must match version tags"

    def test_publish_yml_runs_poetry_publish(self) -> None:
        """publish.yml must run 'poetry publish'."""
        content = PUBLISH_WORKFLOW.read_text()
        assert "poetry publish" in content, "publish.yml must run poetry publish"

    def test_publish_yml_uses_pypi_token(self) -> None:
        """publish.yml must reference PYPI_TOKEN secret."""
        content = PUBLISH_WORKFLOW.read_text()
        assert "PYPI_TOKEN" in content, "publish.yml must reference PYPI_TOKEN"

    def test_publish_yml_runs_poetry_build(self) -> None:
        """publish.yml must run 'poetry build' before publishing."""
        content = PUBLISH_WORKFLOW.read_text()
        assert "poetry build" in content, "publish.yml must run poetry build"

    def test_publish_yml_uses_checkout_action(self) -> None:
        """publish.yml must check out the repository."""
        content = PUBLISH_WORKFLOW.read_text()
        assert "checkout" in content, "publish.yml must use actions/checkout"

    def test_publish_yml_runs_on_ubuntu(self) -> None:
        """publish.yml must run on ubuntu-latest."""
        content = PUBLISH_WORKFLOW.read_text()
        assert "ubuntu" in content, "publish.yml must run on ubuntu"
