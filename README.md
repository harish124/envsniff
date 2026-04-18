# envsniff

> Scan codebases for environment variables, detect undocumented vars, and generate `.env.example` files with AI-written descriptions.

No more "what env vars do I need to run this?" — `envsniff` finds them all and documents them for you.

---

## Table of Contents

- [Why envsniff](#why-envsniff)
- [How it works](#how-it-works)
- [Install](#install)
- [Usage](#usage)
  - [scan](#scan)
  - [generate](#generate)
  - [check](#check)
- [Supported languages](#supported-languages)
- [AI descriptions](#ai-descriptions)
- [Pre-commit hook](#pre-commit-hook)
- [CI integration](#ci-integration)
- [Configuration](#configuration)
- [Output formats](#output-formats)
- [Architecture](#architecture)

---

## Why envsniff

Most teams document environment variables manually — and it's always out of date. `envsniff` fixes this by reading the code directly.

| Tool | Gap |
|------|-----|
| `dotenv-linter` | Lints `.env` files only — does not scan source code |
| `sync-dotenv` | Syncs `.env` → `.env.example`, requires an existing `.env` |
| `detect-secrets` | Security-focused; finds secrets, not documentation |
| `env-checker` | Runtime validation, not a scanner |

**envsniff** is the only tool that scans your source code, finds every `os.getenv()` / `process.env.X` / `os.Getenv()` call, and generates a documented `.env.example` from scratch.

---

## How it works

```mermaid
flowchart TD
    A[Your codebase] --> B[File Walker]
    B -->|respects .gitignore| C[Scanner Registry]
    C --> D1[Python plugin\nos.getenv / os.environ]
    C --> D2[JavaScript plugin\nprocess.env.X]
    C --> D3[Go plugin\nos.Getenv]
    C --> D4[Shell plugin\n$VAR / ${VAR}]
    C --> D5[Docker plugin\nENV / ARG]
    D1 & D2 & D3 & D4 & D5 --> E[Scanner Engine\ndeduplication + type inference]
    E --> F{Command}
    F -->|scan| G[Formatted output\ntable / json / markdown]
    F -->|generate| H[.env.example Parser]
    H --> I[Merger\nnew / stale / existing]
    I --> J[AI Describer\nClaude API]
    J --> K[Atomic Writer\n.env.example]
    F -->|check| L{All vars documented?}
    L -->|yes| M[exit 0 ✓]
    L -->|no| N[exit 1 ✗\nlist undocumented vars]
```

### The merge strategy

When running `envsniff generate`, existing human-written comments are always preserved:

| Var state | Action |
|-----------|--------|
| In code + in `.env.example` | Keep as-is (preserve human description) |
| In code, missing from `.env.example` | Add with `# Added by envsniff` |
| In `.env.example`, not in code | Comment out with `# UNUSED (not found in codebase):` |

---

## Install

```bash
# PyPI
pip install envsniff

# Via npm / npx
npx envsniff scan .
```

---

## Usage

### scan

Find all environment variables in a codebase:

```bash
envsniff scan .
envsniff scan ./src --format json
envsniff scan . --format md
envsniff scan . --exclude "tests/*" --exclude "*.sh"
```

Example output:

```
┌──────────────────┬─────────┬──────────┬─────────┬─────────────────┐
│ Name             │ Type    │ Required │ Default │ Locations       │
├──────────────────┼─────────┼──────────┼─────────┼─────────────────┤
│ DATABASE_URL     │ URL     │ yes      │ —       │ app.py:12       │
│ API_KEY          │ SECRET  │ yes      │ —       │ client.py:8     │
│ DEBUG            │ BOOLEAN │ no       │ false   │ settings.py:3   │
│ PORT             │ INTEGER │ no       │ 8080    │ server.py:1     │
└──────────────────┴─────────┴──────────┴─────────┴─────────────────┘
Scanned 42 files · Found 4 variables
```

### generate

Create or update `.env.example`:

```bash
envsniff generate .
envsniff generate . --output .env.example
envsniff generate . --ai          # use Claude to write descriptions
envsniff generate . --no-ai       # skip AI, use heuristic descriptions
```

Example `.env.example` output:

```bash
# PostgreSQL connection string
# Example: postgresql://user:pass@localhost:5432/mydb
DATABASE_URL=

# API authentication key
API_KEY=

# Enable debug mode
# Example: false
DEBUG=false

# Server port
# Example: 8080
PORT=8080
```

### check

Use in CI or pre-commit to enforce documentation:

```bash
envsniff check .                  # exit 1 if undocumented vars exist
envsniff check . --fail-on-stale  # also exit 1 if stale vars in .env.example
envsniff check . --strict         # fail on any issue
```

---

## Supported languages

| Language | Patterns detected |
|----------|------------------|
| Python | `os.getenv("X")`, `os.environ.get("X")`, `os.environ["X"]` |
| JavaScript / TypeScript | `process.env.X`, `process.env["X"]` |
| Go | `os.Getenv("X")`, `os.LookupEnv("X")` |
| Shell | `$VAR`, `${VAR}` (skips `$$`, `$?`, `$1`–`$9`) |
| Dockerfile | `ENV VAR=value`, `ARG VAR=default` |

---

## AI descriptions

All AI providers are bundled with envsniff. Set the relevant API key and pass `--ai`:

```bash
# Anthropic Claude (default)
export ANTHROPIC_API_KEY=sk-ant-...
envsniff generate . --ai

# OpenAI
export OPENAI_API_KEY=sk-...
envsniff generate . --ai --ai-provider openai

# Google Gemini
export GEMINI_API_KEY=...
envsniff generate . --ai --ai-provider gemini

# Ollama (local, no API key needed)
envsniff generate . --ai --ai-provider ollama

# Grok / Perplexity (OpenAI-compatible)
export OPENAI_BASE_URL=https://api.x.ai/v1
export OPENAI_API_KEY=...
envsniff generate . --ai --ai-provider openai --ai-model grok-beta
```

- Batches up to 20 vars per API call
- Caches results in `~/.cache/envsniff/descriptions.json` (won't call the API twice for the same var)
- Falls back to heuristic descriptions if the API is unavailable

---

## Pre-commit hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/envsniff/envsniff
    rev: v0.1.0
    hooks:
      - id: envsniff-check
```

This blocks commits that introduce undocumented environment variables.

---

## CI integration

```yaml
# .github/workflows/ci.yml
- name: Check env vars are documented
  run: envsniff check . --strict
```

For machine-readable output in CI logs:

```bash
envsniff check . --format json
```

```
status: fail
new_vars[1]: NEW_SECRET
stale_vars[0]:
scanned_files: 42
```

---

## Configuration

Create `.envsniff.toml` in your project root (or add `[tool.envsniff]` to `pyproject.toml`):

```toml
[tool.envsniff]
exclude = ["tests/*", "scripts/*", "*.sh"]
output = ".env.example"
ai = false
```

---

## Output formats

`scan` and `check` support `--format table` (default), `--format json`, and `--format md`.

**JSON** — for scripting and CI:
```
findings[1]:
  - name: DATABASE_URL
    inferred_type: URL
    is_required: true
    default_value: null
    language: python
    locations[1]{file,line}:
      app.py,12
scanned_files: 42
errors[0]:
```

**Markdown** — for documentation:
```markdown
| Name | Type | Required | Default |
|------|------|----------|---------|
| DATABASE_URL | URL | yes | — |
| DEBUG | BOOLEAN | no | false |
```

---

## Architecture

```
src/envsniff/
├── models.py           # Immutable dataclasses (SourceLocation, EnvVarFinding, ScanResult)
├── errors.py           # Exception hierarchy
├── config.py           # .envsniff.toml / pyproject.toml loader
├── scanner/
│   ├── engine.py       # Orchestrates walk → dispatch → deduplicate
│   ├── file_walker.py  # .gitignore-aware recursive walk (pathspec)
│   ├── registry.py     # Maps file extensions to plugins
│   ├── type_inferrer.py
│   └── plugins/        # One file per language
├── env_example/
│   ├── parser.py       # Reads existing .env.example preserving structure
│   ├── merger.py       # new / stale / existing classification
│   └── writer.py       # Atomic write (temp → rename)
├── describer/
│   ├── types.py        # Name → InferredType rules
│   ├── fallback.py     # Heuristic descriptions (no API needed)
│   ├── cache.py        # SHA-256 keyed JSON cache
│   └── ai.py           # Claude API batched descriptions
├── hooks/
│   ├── precommit.py    # Staged-files-only scan
│   └── ci.py           # Full scan with JSON output
└── cli/
    ├── main.py         # Click commands: scan / generate / check
    └── formatters.py   # table / json / markdown renderers
```
