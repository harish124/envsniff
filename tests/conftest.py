"""Shared test fixtures and configuration for envsniff tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to the tests/fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory for integration tests."""
    (tmp_path / "src").mkdir()
    return tmp_path
