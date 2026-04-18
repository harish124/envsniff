"""Plugin registry: maps file extensions and filenames to scanner plugin instances."""

from __future__ import annotations

from typing import TYPE_CHECKING

from envsniff.scanner.plugins.base import LanguageScanner
from envsniff.scanner.plugins.docker import DockerPlugin
from envsniff.scanner.plugins.golang import GoPlugin
from envsniff.scanner.plugins.javascript import JavaScriptPlugin
from envsniff.scanner.plugins.python import PythonPlugin
from envsniff.scanner.plugins.shell import ShellPlugin

if TYPE_CHECKING:
    from pathlib import Path


class PluginRegistry:
    """Resolves a file path to the appropriate language scanner plugin.

    Each plugin registers itself for a set of file extensions and/or specific
    filenames (e.g. Dockerfile has no extension).
    """

    def __init__(self) -> None:
        self._plugins: list[LanguageScanner] = [
            PythonPlugin(),
            JavaScriptPlugin(),
            GoPlugin(),
            ShellPlugin(),
            DockerPlugin(),
        ]
        # Build extension → plugin map
        self._ext_map: dict[str, LanguageScanner] = {}
        for plugin in self._plugins:
            for ext in plugin.supported_extensions:
                self._ext_map[ext] = plugin

        # Build filename → plugin map for plugins with supported_filenames
        self._name_map: dict[str, LanguageScanner] = {}
        for plugin in self._plugins:
            filenames: frozenset[str] = getattr(plugin, "supported_filenames", frozenset())
            for fname in filenames:
                self._name_map[fname] = plugin

    def get_plugin(self, file: Path) -> LanguageScanner | None:
        """Return the plugin for the given file path, or None if unsupported.

        Filename-based lookup takes priority over extension-based lookup.
        """
        # Filename match (e.g. "Dockerfile", "Dockerfile.dev")
        name = file.name
        if name in self._name_map:
            return self._name_map[name]

        # Also check if filename starts with "Dockerfile"
        if name.startswith("Dockerfile") or name.startswith("dockerfile"):
            docker_plugin = next(
                (p for p in self._plugins if isinstance(p, DockerPlugin)), None
            )
            if docker_plugin:
                return docker_plugin

        # Extension match
        ext = file.suffix.lower()
        return self._ext_map.get(ext)
