"""CLI entry point for envsniff.

Commands:
    scan     — Scan a path for environment variable usage.
    generate — Scan + generate/update a .env.example file.
    check    — Scan + diff against existing .env.example; exit non-zero if issues.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from envsniff.cli.formatters import format_json, format_markdown, format_table
from envsniff.config import load_config
from envsniff.env_example.merger import MergeStatus, MergedEntry, merge_findings
from envsniff.env_example.parser import parse_env_example
from envsniff.env_example.writer import write_env_example
from envsniff.errors import ParseError
from envsniff.models import ScanResult
from envsniff.scanner.engine import ScanEngine

_PROVIDER_EXAMPLES: dict[str, str] = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
    "ollama": "llama3.2",
}


def _prompt_ai_settings(
    provider: str | None,
    model: str | None,
    config_provider: str,
    config_model: str | None,
) -> tuple[str, str | None]:
    """Interactively prompt for provider and model when running in a terminal.

    Returns resolved (provider, model) — model may be None (use provider default).
    Skips prompts and falls back to config/defaults when stdin is not a tty.
    """
    import questionary

    interactive = sys.stdin.isatty()

    # --- Provider ---
    resolved_provider = provider or config_provider
    if provider is None and interactive:
        chosen = questionary.select(
            "Which AI provider?",
            choices=[
                questionary.Choice("1. Anthropic (Claude)", value="anthropic"),
                questionary.Choice("2. OpenAI (GPT)", value="openai"),
                questionary.Choice("3. Google Gemini", value="gemini"),
                questionary.Choice("4. Ollama (local)", value="ollama"),
            ],
            default="anthropic",
        ).ask()
        if chosen is None:
            raise click.Abort()
        resolved_provider = chosen

    # --- Model ---
    resolved_model: str | None = model or config_model
    if model is None and interactive:
        example = _PROVIDER_EXAMPLES.get(resolved_provider, "")
        click.echo(f"  Tip: check the official {resolved_provider} documentation for available models.")
        raw = questionary.text(
            "Which model?",
            instruction=f"(e.g. {example})",
        ).ask()
        if raw is None:
            raise click.Abort()
        if not raw.strip():
            raise click.UsageError("Model name is required. Check your provider's documentation for available models.")
        resolved_model = raw.strip()

    return resolved_provider, resolved_model


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(package_name="envsniff")
def cli() -> None:
    """envsniff — scan codebases for environment variables."""


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "md"]),
    default="table",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--exclude",
    multiple=True,
    metavar="PATTERN",
    help="Glob pattern to exclude (repeatable).",
)
def scan(path: str, output_format: str, exclude: tuple[str, ...]) -> None:
    """Scan PATH for environment variable usage."""
    resolved = Path(path)
    engine = ScanEngine(exclude=list(exclude))
    result: ScanResult = engine.scan(resolved)

    if output_format == "json":
        click.echo(format_json(result))
    elif output_format == "md":
        click.echo(format_markdown(result))
    else:
        click.echo(format_table(result))


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    default=None,
    metavar="FILE",
    help="Output file path (default: <PATH>/.env.example).",
)
@click.option(
    "--ai/--no-ai",
    default=False,
    help="Use AI to generate descriptions (requires provider package).",
)
@click.option(
    "--ai-provider",
    default=None,
    type=click.Choice(["anthropic", "openai", "gemini", "ollama"]),
    help="AI provider (default: from config or 'anthropic').",
)
@click.option(
    "--ai-model",
    default=None,
    metavar="MODEL",
    help="Model name override (default: provider default).",
)
def generate(path: str, output: str | None, ai: bool, ai_provider: str | None, ai_model: str | None) -> None:
    """Generate or update .env.example for PATH."""
    resolved = Path(path)
    config = load_config(resolved)

    # Determine output path
    if output is not None:
        output_path = Path(output)
    else:
        output_path = resolved / config.output

    # Scan
    engine = ScanEngine(exclude=list(config.exclude))
    result: ScanResult = engine.scan(resolved)

    # Parse existing .env.example (if any)
    existing_entries = []
    if output_path.is_file():
        try:
            existing_entries = parse_env_example(output_path)
        except ParseError:
            existing_entries = []

    # Merge
    merged = merge_findings(list(result.findings), existing_entries)

    # Apply AI descriptions to NEW entries
    use_ai = ai or config.ai
    if use_ai:
        from envsniff.describer.ai import describe_batch
        provider, model = _prompt_ai_settings(
            ai_provider, ai_model, config.ai_provider, config.ai_model
        )
        existing_keys = {e.key for e in existing_entries}
        new_findings = [f for f in result.findings if f.name not in existing_keys]
        descriptions = describe_batch(new_findings, provider=provider, model=model)
        merged = [
            MergedEntry(
                key=entry.key,
                value=entry.value,
                comments=(f"# {descriptions[entry.key][0]}", f"# Example: {descriptions[entry.key][1]}")
                if entry.status == MergeStatus.NEW and entry.key in descriptions
                else entry.comments,
                inline_comment=entry.inline_comment,
                blank_line_before=entry.blank_line_before,
                status=entry.status,
            )
            for entry in merged
        ]

    # Write
    write_env_example(merged, output_path)

    click.echo(
        f"Wrote {len(merged)} variable(s) to {output_path} "
        f"(scanned {result.scanned_files} file(s))."
    )


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

# Exit codes:
#   0 — clean
#   1 — new (undocumented) vars found
#   2 — stale vars found (only when --fail-on-stale or stale + --strict)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option(
    "--strict",
    is_flag=True,
    help="Exit non-zero on any issue (new or stale).",
)
@click.option(
    "--fail-on-stale",
    is_flag=True,
    help="Exit 2 if stale variables exist in .env.example.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    show_default=True,
    help="Output format.",
)
def check(path: str, strict: bool, fail_on_stale: bool, output_format: str) -> None:
    """Check PATH for undocumented environment variables.

    Exit codes:
        0 — all variables are documented (clean)
        1 — undocumented (new) variables found
        2 — stale variables found (requires --fail-on-stale or --strict)
    """
    resolved = Path(path)
    config = load_config(resolved)
    env_example_path = resolved / config.output

    # Scan
    engine = ScanEngine(exclude=list(config.exclude))
    result: ScanResult = engine.scan(resolved)

    # Parse existing .env.example (missing file → empty list = all vars are new)
    existing_entries = []
    if env_example_path.is_file():
        try:
            existing_entries = parse_env_example(env_example_path)
        except ParseError:
            existing_entries = []

    # Merge to get new/stale/existing classification
    merged = merge_findings(list(result.findings), existing_entries)

    new_vars = [e for e in merged if e.status == MergeStatus.NEW]
    stale_vars = [e for e in merged if e.status == MergeStatus.STALE]

    # ---------- Report ----------
    if output_format == "json":
        click.echo(json.dumps({
            "status": "fail" if new_vars else "pass",
            "new_vars": [e.key for e in new_vars],
            "stale_vars": [e.key for e in stale_vars],
            "scanned_files": result.scanned_files,
        }))
    else:
        if new_vars:
            click.echo(f"New undocumented variable(s) ({len(new_vars)}):")
            for entry in new_vars:
                click.echo(f"  + {entry.key}")

        if stale_vars:
            click.echo(f"Stale variable(s) in .env.example ({len(stale_vars)}):")
            for entry in stale_vars:
                click.echo(f"  - {entry.key}")

        if not new_vars and not stale_vars:
            click.echo("All environment variables are documented. Clean!")

    # ---------- Exit code ----------
    if new_vars:
        sys.exit(1)

    if stale_vars and (fail_on_stale or strict):
        sys.exit(2)
