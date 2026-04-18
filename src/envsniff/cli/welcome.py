"""Welcome banner shown on first run after install."""

from __future__ import annotations

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


def show_if_first_run() -> None:
    """Print the welcome banner the first time envsniff is run.

    Writes a marker file to ~/.config/envsniff/.welcomed so the banner
    is shown exactly once per machine.
    """
    if _MARKER.exists():
        return

    console = Console(stderr=True)
    console.print(Text(_LOGO, style="bold green"))
    console.print(
        "[bold white]Welcome to envsniff![/bold white] "
        "Scan your codebase for environment variables and keep "
        "[cyan].env.example[/cyan] in sync.\n",
        highlight=False,
    )

    try:
        _MARKER.parent.mkdir(parents=True, exist_ok=True)
        _MARKER.touch()
    except OSError:
        pass  # read-only fs or permissions issue — silently skip
