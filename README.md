# envsniff

![envsniff](assets/envsniff-ascii.png)

[![Stars](https://img.shields.io/github/stars/harish124/envsniff?style=flat-square&logo=github)](https://github.com/harish124/envsniff/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/harish124/envsniff?style=flat-square&logo=github)](https://github.com/harish124/envsniff/commits/main)
[![License](https://img.shields.io/github/license/harish124/envsniff?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)

> Scan codebases for environment variables, detect undocumented vars, and generate `.env.example` files — with or without AI-written descriptions.

No more "what env vars do I need to run this?" — `envsniff` finds them all and documents them for you.

---

## Table of Contents

- [Why envsniff](#why-envsniff)
- [Architecture](#architecture)
- [How it works](#how-it-works)
- [Install](#install)
- [Usage](#usage)
  - [scan](#scan)
  - [generate](#generate)
  - [check](#check)
- [Supported languages](#supported-languages)
- [Technologies](#technologies)
- [AI descriptions](#ai-descriptions)
- [Pre-commit hook](#pre-commit-hook)
- [GitHub Action](#github-action)
- [CI integration](#ci-integration)
- [Configuration](#configuration)
- [Output formats](#output-formats)

---

## Why envsniff

Most teams document environment variables manually — and it's always out of date. `envsniff` fixes this by reading the code directly.

| Tool             | Gap                                                        |
| ---------------- | ---------------------------------------------------------- |
| `dotenv-linter`  | Lints `.env` files only — does not scan source code        |
| `sync-dotenv`    | Syncs `.env` → `.env.example`, requires an existing `.env` |
| `detect-secrets` | Security-focused; finds secrets, not documentation         |
| `env-checker`    | Runtime validation, not a scanner                          |

**envsniff** is the only tool that scans your source code, finds every `os.getenv()` / `process.env.X` / `os.Getenv()` call, and generates a documented `.env.example` from scratch.

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
│   └── ai.py           # Multi-provider AI descriptions (Anthropic, OpenAI, Gemini, Ollama)
├── hooks/
│   ├── precommit.py    # Staged-files-only scan
│   └── ci.py           # Full scan with JSON output
└── cli/
    ├── main.py         # Click commands: scan / generate / check
    └── formatters.py   # table / json / markdown renderers
```

---

## How it works

```mermaid
flowchart TD
    A[Your codebase] --> B[File Walker]
    B -->|respects .gitignore| C[Scanner Registry]
    C --> D1[Python plugin\nos.getenv / os.environ]
    C --> D2[JavaScript plugin\nprocess.env.X]
    C --> D3[Go plugin\nos.Getenv]
    C --> D4[Shell plugin\n$VAR / $VARNAME]
    C --> D5[Docker plugin\nENV / ARG]
    D1 & D2 & D3 & D4 & D5 --> E[Scanner Engine\ndeduplication + type inference]
    E --> F{Command}
    F -->|scan| G[Formatted output\ntable / json / markdown]
    F -->|generate| H[.env.example Parser]
    H --> I[Merger\nnew / stale / existing]
    I --> J[AI Describer\noptional]
    J --> K[Atomic Writer\n.env.example]
    F -->|check| L{All vars documented?}
    L -->|yes| M[exit 0 ✓]
    L -->|no| N[exit 1 ✗\nlist undocumented vars]
```

### The merge strategy

When running `envsniff generate`, existing human-written comments are always preserved:

| Var state                            | Action                                               |
| ------------------------------------ | ---------------------------------------------------- |
| In code + in `.env.example`          | Keep as-is (preserve human description)              |
| In code, missing from `.env.example` | Add with `# Added by envsniff`                       |
| In `.env.example`, not in code       | Comment out with `# UNUSED (not found in codebase):` |

---

## Install

### macOS / Linux

```bash
pip install envsniff
```

### Windows

```cmd
pip install envsniff
```

### Via npm / npx (any OS)

```bash
npx envsniff scan .
```

### Local development (after cloning)

```bash
# macOS / Linux
git clone https://github.com/harish124/envsniff.git
cd envsniff
pip install -e .

# Windows
git clone https://github.com/harish124/envsniff.git
cd envsniff
pip install -e .
```

The `-e` flag installs in editable mode — changes to the source take effect immediately without reinstalling.

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
envsniff generate . --ai          # prompts for provider + model interactively
envsniff generate . --no-ai       # skip AI, use heuristic descriptions
envsniff generate . --ai --ai-provider openai --ai-model gpt-4o   # non-interactive
```

Example `.env.example` output:

```bash
# Added by envsniff
#
# Description: PostgreSQL/MySQL connection string
# Example:     postgres://user:pass@localhost/dbname
#
DATABASE_URL=

# Added by envsniff
#
# Description: Api API key
#
API_KEY=

# Added by envsniff
#
# Description: Enable debug mode (true/false)
# Example:     false
#
DEBUG=false

# Added by envsniff
#
# Description: Port number the server listens on
# Example:     8080
#
PORT=8080
```

Heuristic descriptions are always generated — no `--ai` flag needed. The `# Example:` line is omitted when no example value is known.

### check

Use in CI or pre-commit to enforce documentation:

```bash
envsniff check .                  # exit 1 if undocumented vars exist
envsniff check . --fail-on-stale  # also exit 1 if stale vars in .env.example
envsniff check . --strict         # fail on any issue
```

---

## Supported languages

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Go](https://img.shields.io/badge/Go-00ADD8?style=flat-square&logo=go&logoColor=white)
![Shell](https://img.shields.io/badge/Shell-4EAA25?style=flat-square&logo=gnu-bash&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)

| Language                | Patterns detected                                          |
| ----------------------- | ---------------------------------------------------------- |
| Python                  | `os.getenv("X")`, `os.environ.get("X")`, `os.environ["X"]` |
| JavaScript / TypeScript | `process.env.X`, `process.env["X"]`                        |
| Go                      | `os.Getenv("X")`, `os.LookupEnv("X")`                      |
| Shell                   | `$VAR`, `${VAR}` — skips local variables (`VAR=value` without `export`), shell specials (`$$`, `$?`, `$1`–`$9`) |
| Dockerfile              | `ENV VAR=value`, `ARG VAR=default`                         |

---

## Technologies

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Click](https://img.shields.io/badge/Click-000000?style=flat-square&logo=python&logoColor=white)
![tree--sitter](https://img.shields.io/badge/tree--sitter-lightgrey?style=flat-square)
![Anthropic](https://img.shields.io/badge/Anthropic-Claude-black?style=flat-square)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-4285F4?style=flat-square&logo=google&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-local-darkgreen?style=flat-square)

| Library                                                                      | Purpose                                                |
| ---------------------------------------------------------------------------- | ------------------------------------------------------ |
| [Click](https://click.palletsprojects.com)                                   | CLI framework                                          |
| [tree-sitter](https://tree-sitter.github.io)                                 | AST-based source code parsing per language             |
| [questionary](https://github.com/tmbo/questionary)                           | Interactive terminal prompts with arrow-key navigation |
| [pathspec](https://github.com/cpburnz/python-pathspec)                       | `.gitignore`-aware file walking                        |
| [anthropic](https://github.com/anthropics/anthropic-sdk-python)              | Anthropic Claude AI descriptions                       |
| [openai](https://github.com/openai/openai-python)                            | OpenAI / Grok / Perplexity AI descriptions             |
| [google-generativeai](https://github.com/google-gemini/generative-ai-python) | Google Gemini AI descriptions                          |
| [ollama](https://github.com/ollama/ollama-python)                            | Local Ollama AI descriptions                           |

---

## AI descriptions

All AI providers are bundled with envsniff — no extra install step. Pass `--ai` and you will be prompted to choose a provider and model interactively:

```
$ envsniff generate . --ai

? Which AI provider?
  1. Anthropic (Claude)
❯ 2. OpenAI (GPT)
  3. Google Gemini
  4. Ollama (local)

  Tip: check the official openai documentation for available models.
? Which model? (e.g. gpt-4o-mini): gpt-4o
```

Use arrow keys to select a provider, Enter to confirm. Model name is required — leaving it blank will error.

Or skip the prompts by passing flags directly (useful for CI):

```bash
envsniff generate . --ai --ai-provider openai --ai-model gpt-4o
```

Set the API key for your chosen provider before running:

| Provider  | API key env var     | Notes                                                 |
| --------- | ------------------- | ----------------------------------------------------- |
| Anthropic | `ANTHROPIC_API_KEY` | Default provider                                      |
| OpenAI    | `OPENAI_API_KEY`    | Also works for Grok, Perplexity via `OPENAI_BASE_URL` |
| Gemini    | `GEMINI_API_KEY`    |                                                       |
| Ollama    | —                   | Local, no key needed                                  |

- Batches up to 20 vars per API call
- Caches results in `~/.cache/envsniff/descriptions.json` — API is never called twice for the same var
- Falls back to heuristic descriptions if the provider is unavailable

### Privacy

envsniff scrubs code snippets before sending anything to the AI provider. Default values (the second argument in calls like `os.environ.get("KEY", "value")`) are stripped using regex so only the variable name and call structure are transmitted:

```python
# What's in your code:
db = os.environ.get("DATABASE_URL", "postgres://user:secret@prod/db")

# What the AI receives:
os.environ.get("DATABASE_URL")
```

**What is never sent:** `.env` file contents, actual secret values, or any string literals used as defaults.

> **Disclaimer — known limitation:** The scrubbing works on single-line calls. If a default value spans multiple lines, the regex cannot reliably detect it and that line may be sent as-is:
>
> ```python
> # Multi-line call — default value on its own line may not be scrubbed:
> url = os.environ.get(
>     "DATABASE_URL",
>     "postgres://user:secret@prod/db"   # ← this line could be sent
> )
> ```
>
> This is an inherent limitation of line-by-line text scrubbing. The fix would require full AST-level analysis, which is not currently implemented. To be safe, avoid hardcoding real secrets as default values in your source code — use placeholder strings like `"postgres://localhost/mydb"` instead.

---

## Pre-commit hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/harish124/envsniff
    rev: v0.1.0
    hooks:
      - id: envsniff-check
```

This blocks commits that introduce undocumented environment variables.

---

## GitHub Action

Add envsniff to any repository in seconds. On every pull request it scans your code, updates `.env.example`, and commits the result automatically — no manual step needed.

```yaml
# .github/workflows/envsniff.yml
name: Sync .env.example

on:
  pull_request:
    branches: [main, master]

jobs:
  envsniff:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}
          fetch-depth: 0

      - uses: harish124/envsniff@v1
        with:
          path: "."
          commit: "true" # auto-commit updated .env.example
          fail-on-drift: "false" # set "true" to block merges on undocumented vars
          commit-message: "chore: sync .env.example [skip ci]"
```

### Action inputs

| Input            | Default                    | Description                                               |
| ---------------- | -------------------------- | --------------------------------------------------------- |
| `path`           | `.`                        | Directory to scan                                         |
| `commit`         | `true`                     | Commit updated `.env.example` back to the PR branch       |
| `fail-on-drift`  | `false`                    | Block the merge when new undocumented variables are found |
| `commit-message` | `chore: sync .env.example` | Commit message for the auto-commit                        |
| `python-version` | `3.12`                     | Python version used to install envsniff                   |

### Action outputs

| Output           | Description                                                             |
| ---------------- | ----------------------------------------------------------------------- |
| `new-vars`       | Comma-separated list of newly found variables not yet in `.env.example` |
| `stale-vars`     | Comma-separated list of variables in `.env.example` no longer in code   |
| `scanned-files`  | Number of source files scanned                                          |
| `drift-detected` | `true` when new undocumented variables were found                       |

> **Requires:** Repository Settings → Actions → General → Workflow permissions → **Read and write permissions**

A ready-to-copy workflow file is available at [`.github/examples/envsniff.yml`](.github/examples/envsniff.yml).

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
ai_provider = "anthropic"   # anthropic | openai | gemini | ollama
ai_model = ""               # leave empty to be prompted, or set a specific model
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
| Name         | Type    | Required | Default |
| ------------ | ------- | -------- | ------- |
| DATABASE_URL | URL     | yes      | —       |
| DEBUG        | BOOLEAN | no       | false   |
```
