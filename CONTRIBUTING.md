# Contributing to envsniff

Thank you for taking the time to contribute! This document covers everything you need to get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Adding a Language Plugin](#adding-a-language-plugin)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Bugs](#reporting-bugs)

---

## Code of Conduct

Be respectful and constructive. We welcome contributors of all experience levels.

---

## How to Contribute

1. **Fork** the repository
2. **Create** your feature branch
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit** your changes
   ```bash
   git commit -m 'feat: add amazing feature'
   ```
4. **Push** to the branch
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open a Pull Request** against `master`

---

## Development Setup

**Requirements:** Python 3.11+, [Poetry](https://python-poetry.org/)

```bash
# Clone your fork
git clone https://github.com/<your-username>/envsniff.git
cd envsniff

# Install all dependencies (including dev)
poetry install

# Verify everything works
poetry run pytest
poetry run ruff check src/
poetry run mypy src/
```

---

## Project Structure

```
src/envsniff/
├── cli/
│   ├── main.py          # Click commands: scan / generate / check
│   ├── formatters.py    # table / json / markdown output renderers
│   └── welcome.py       # First-run banner
├── scanner/
│   ├── engine.py        # Orchestrates walk → dispatch → deduplicate
│   ├── file_walker.py   # .gitignore-aware recursive file walk
│   ├── registry.py      # Maps file extensions/names to plugins
│   └── plugins/         # One file per supported language
├── env_example/
│   ├── parser.py        # Reads existing .env.example
│   ├── merger.py        # Classifies vars as new / existing / stale
│   └── writer.py        # Atomic write (temp file → rename)
├── describer/
│   ├── ai.py            # Multi-provider AI descriptions
│   ├── fallback.py      # Heuristic descriptions (no API needed)
│   └── cache.py         # SHA-256 keyed JSON cache
├── hooks/
│   ├── precommit.py     # Staged-files-only scan
│   └── ci.py            # Full scan with JSON output
├── models.py            # Immutable dataclasses
├── config.py            # .envsniff.toml / pyproject.toml loader
└── errors.py            # Exception hierarchy
```

---

## Running Tests

```bash
# Run all tests with coverage
poetry run pytest

# Run a specific test file
poetry run pytest tests/unit/test_scanner.py

# Run without coverage (faster)
poetry run pytest --no-cov
```

Coverage must remain at **80% or above**. New features should include tests.

---

## Code Style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and [mypy](https://mypy.readthedocs.io/) (strict mode) for type checking.

```bash
# Lint
poetry run ruff check src/

# Auto-fix lint issues
poetry run ruff check src/ --fix

# Type check
poetry run mypy src/
```

All three must pass before opening a PR. The CI pipeline enforces this.

**Key conventions:**
- All type annotations required (mypy strict)
- Imports sorted by ruff (`I` rules)
- Use `TYPE_CHECKING` blocks for annotation-only imports
- Immutable dataclasses (`frozen=True`) for data models
- No mutation of existing objects — return new ones

---

## Adding a Language Plugin

The easiest way to contribute is adding support for a new language. Each plugin is a single file in `src/envsniff/scanner/plugins/`.

1. **Create** `src/envsniff/scanner/plugins/<language>.py`

   ```python
   from __future__ import annotations
   from typing import TYPE_CHECKING
   from envsniff.models import EnvVarFinding, SourceLocation
   from envsniff.scanner.type_inferrer import infer_type

   if TYPE_CHECKING:
       from pathlib import Path

   class RubyPlugin:
       @property
       def language(self) -> str:
           return "ruby"

       @property
       def supported_extensions(self) -> frozenset[str]:
           return frozenset({".rb"})

       def scan(self, file: Path) -> list[EnvVarFinding]:
           # Parse the file, return findings
           ...
   ```

2. **Register** it in `src/envsniff/scanner/registry.py`

   ```python
   from envsniff.scanner.plugins.ruby import RubyPlugin
   # Add RubyPlugin() to self._plugins list
   ```

3. **Add tests** in `tests/unit/test_<language>_plugin.py` and a fixture file in `tests/fixtures/`

4. **Update** the supported languages table in `README.md`

---

## Submitting a Pull Request

- Keep PRs focused — one feature or fix per PR
- Write a clear PR description explaining the *why*, not just the *what*
- Ensure all CI checks pass (tests, ruff, mypy)
- Add or update tests for any changed behaviour
- Update `README.md` if you're adding user-facing functionality

---

## Reporting Bugs

Open an issue at [github.com/harish124/envsniff/issues](https://github.com/harish124/envsniff/issues) with:

- envsniff version (`envsniff --version`)
- Python version (`python --version`)
- OS
- Minimal reproduction steps
- Expected vs actual behaviour
