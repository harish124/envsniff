"""Unit tests for the .gitignore-aware file walker — TDD RED phase."""

from __future__ import annotations

from pathlib import Path

import pytest

from envsniff.scanner.file_walker import FileWalker


class TestFileWalkerHappyPath:
    """Tests for basic file walking functionality."""

    def test_walks_all_python_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert tmp_path / "a.py" in files
        assert tmp_path / "b.py" in files

    def test_walks_subdirectories(self, tmp_path: Path) -> None:
        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "main.py").write_text("pass")
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert sub / "main.py" in files

    def test_returns_path_objects(self, tmp_path: Path) -> None:
        (tmp_path / "test.py").write_text("pass")
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert all(isinstance(f, Path) for f in files)

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        walker = FileWalker(tmp_path)
        assert list(walker.walk()) == []

    def test_single_file_input(self, tmp_path: Path) -> None:
        f = tmp_path / "single.py"
        f.write_text("x = 1")
        walker = FileWalker(f)
        files = list(walker.walk())
        assert f in files
        assert len(files) == 1


class TestFileWalkerDefaultExclusions:
    """Tests that default excluded directories are skipped."""

    def test_skips_node_modules(self, tmp_path: Path) -> None:
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "package.js").write_text("// npm")
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert not any("node_modules" in str(f) for f in files)

    def test_skips_venv(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "lib.py").write_text("pass")
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert not any(".venv" in str(f) for f in files)

    def test_skips_pycache(self, tmp_path: Path) -> None:
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "mod.pyc").write_text("")
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert not any("__pycache__" in str(f) for f in files)

    def test_skips_dist(self, tmp_path: Path) -> None:
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "bundle.js").write_text("")
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert not any("dist" in str(f) for f in files)

    def test_skips_build(self, tmp_path: Path) -> None:
        build = tmp_path / "build"
        build.mkdir()
        (build / "output.js").write_text("")
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert not any(str(f).endswith("build/output.js") for f in files)

    def test_skips_git_directory(self, tmp_path: Path) -> None:
        git = tmp_path / ".git"
        git.mkdir()
        (git / "config").write_text("")
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert not any(".git" in str(f) for f in files)


class TestFileWalkerGitignore:
    """Tests for .gitignore-aware exclusion using pathspec."""

    def test_respects_gitignore_patterns(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.log\n")
        (tmp_path / "app.log").write_text("log data")
        (tmp_path / "app.py").write_text("pass")
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert tmp_path / "app.py" in files
        assert tmp_path / "app.log" not in files

    def test_respects_directory_gitignore_pattern(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("secrets/\n")
        secrets = tmp_path / "secrets"
        secrets.mkdir()
        (secrets / "keys.py").write_text("pass")
        (tmp_path / "main.py").write_text("pass")
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert tmp_path / "main.py" in files
        assert not any("secrets" in str(f) for f in files)

    def test_no_gitignore_walks_all(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("pass")
        (tmp_path / "b.js").write_text("pass")
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert len(files) == 2


class TestFileWalkerCustomExclusions:
    """Tests for caller-supplied exclude patterns."""

    def test_custom_exclude_pattern(self, tmp_path: Path) -> None:
        (tmp_path / "test_foo.py").write_text("pass")
        (tmp_path / "foo.py").write_text("pass")
        walker = FileWalker(tmp_path, exclude=["test_*.py"])
        files = list(walker.walk())
        assert tmp_path / "foo.py" in files
        assert tmp_path / "test_foo.py" not in files

    def test_multiple_custom_excludes(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("pass")
        (tmp_path / "b.js").write_text("pass")
        (tmp_path / "c.go").write_text("pass")
        walker = FileWalker(tmp_path, exclude=["*.js", "*.go"])
        files = list(walker.walk())
        assert tmp_path / "a.py" in files
        assert tmp_path / "b.js" not in files
        assert tmp_path / "c.go" not in files


class TestFileWalkerExtensionFilter:
    """Tests for extension-based filtering."""

    def test_extension_filter_includes_only_matching(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("pass")
        (tmp_path / "b.js").write_text("pass")
        (tmp_path / "c.go").write_text("pass")
        walker = FileWalker(tmp_path, extensions={".py"})
        files = list(walker.walk())
        assert tmp_path / "a.py" in files
        assert tmp_path / "b.js" not in files
        assert tmp_path / "c.go" not in files

    def test_no_extension_filter_returns_all(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("pass")
        (tmp_path / "b.js").write_text("pass")
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert len(files) == 2
