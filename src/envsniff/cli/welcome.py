"""Welcome banner shown on first run and after upgrades."""

from __future__ import annotations

from importlib.metadata import version as pkg_version
from pathlib import Path

from rich.console import Console
from rich.text import Text

_MARKER = Path.home() / ".config" / "envsniff" / ".welcomed"

_LOGO = r"""
███████╗███╗   ██╗██╗   ██╗███████╗███╗   ██╗██╗███████╗███████╗     █████╗ ██╗
██╔════╝████╗  ██║██║   ██║██╔════╝████╗  ██║██║██╔════╝██╔════╝    ██╔══██╗██║
█████╗  ██╔██╗ ██║██║   ██║███████╗██╔██╗ ██║██║█████╗  █████╗      ███████║██║
██╔══╝  ██║╚██╗██║╚██╗ ██╔╝╚════██║██║╚██╗██║██║██╔══╝  ██╔══╝      ██╔══██║██║
███████╗██║ ╚████║ ╚████╔╝ ███████║██║ ╚████║██║██║     ██║         ██║  ██║██║
╚══════╝╚═╝  ╚═══╝  ╚═══╝  ╚══════╝╚═╝  ╚═══╝╚═╝╚═╝     ╚═╝         ╚═╝  ╚═╝╚═╝
"""


def _installed_version() -> str:
    try:
        return pkg_version("envsniff")
    except Exception:
        return "unknown"


def _marker_version() -> str:
    try:
        return _MARKER.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _write_marker(ver: str) -> None:
    try:
        _MARKER.parent.mkdir(parents=True, exist_ok=True)
        _MARKER.write_text(ver, encoding="utf-8")
    except OSError:
        pass  # read-only fs or permissions issue — silently skip


def show_if_first_run() -> None:
    """Print the welcome banner on first install or after an upgrade.

    Stores the installed version in ~/.config/envsniff/.welcomed.
    Banner is shown whenever the stored version differs from the
    currently installed version (covers fresh installs and upgrades).
    """
    current = _installed_version()
    if _marker_version() == current:
        return

    console = Console(stderr=True)
    console.print(Text(_LOGO, style="bold green"))
    console.print(
        f"[bold white]Welcome to envsniff {current}![/bold white] "
        "Scan your codebase for environment variables and keep "
        "[cyan].env.example[/cyan] in sync.\n",
        highlight=False,
    )

    _write_marker(current)
