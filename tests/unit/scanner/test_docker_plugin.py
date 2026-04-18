"""Unit tests for the Dockerfile scanner plugin — TDD RED phase."""

from __future__ import annotations

from pathlib import Path

import pytest

from envsniff.scanner.plugins.docker import DockerPlugin


FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


class TestDockerPluginHappyPath:
    """Tests for ENV and ARG patterns in Dockerfiles."""

    def setup_method(self) -> None:
        self.plugin = DockerPlugin()
        self.sample = FIXTURES / "Dockerfile_sample"

    def test_supported_filenames(self) -> None:
        assert "Dockerfile" in self.plugin.supported_filenames

    def test_language_name(self) -> None:
        assert self.plugin.language == "docker"

    def test_finds_arg_without_default(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "BUILD_VERSION" in names

    def test_finds_arg_with_default(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "NODE_ENV" in names

    def test_arg_default_value_extracted(self) -> None:
        findings = self.plugin.scan(self.sample)
        node_env = next(f for f in findings if f.name == "NODE_ENV")
        assert node_env.default_value == "production"

    def test_finds_env_var(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "APP_PORT" in names

    def test_env_default_value_extracted(self) -> None:
        findings = self.plugin.scan(self.sample)
        app_port = next(f for f in findings if f.name == "APP_PORT")
        assert app_port.default_value == "8080"

    def test_finds_database_url(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "DATABASE_URL" in names

    def test_finds_base_image_arg(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "BASE_IMAGE" in names

    def test_finds_secret_key(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "SECRET_KEY" in names

    def test_finds_api_base_url(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = {f.name for f in findings}
        assert "API_BASE_URL" in names

    def test_no_duplicate_names(self) -> None:
        findings = self.plugin.scan(self.sample)
        names = [f.name for f in findings]
        assert len(names) == len(set(names))

    def test_source_location_file_is_correct(self) -> None:
        findings = self.plugin.scan(self.sample)
        build_ver = next(f for f in findings if f.name == "BUILD_VERSION")
        assert build_ver.locations[0].file == self.sample

    def test_finding_language_is_docker(self) -> None:
        findings = self.plugin.scan(self.sample)
        assert all(f.language == "docker" for f in findings)


class TestDockerPluginEdgeCases:
    """Edge cases for DockerPlugin."""

    def setup_method(self) -> None:
        self.plugin = DockerPlugin()

    def test_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "Dockerfile"
        f.write_text("")
        assert self.plugin.scan(f) == []

    def test_lowercase_arg_skipped(self) -> None:
        findings = self.plugin.scan(FIXTURES / "Dockerfile_sample")
        names = {f.name for f in findings}
        assert "lowercase_arg" not in names

    def test_nonexistent_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.plugin.scan(Path("/nonexistent/Dockerfile"))

    def test_dockerfile_with_only_from_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "Dockerfile"
        f.write_text("FROM ubuntu:22.04\nWORKDIR /app\nCMD ['bash']\n")
        assert self.plugin.scan(f) == []

    def test_arg_without_default_is_required(self, tmp_path: Path) -> None:
        f = tmp_path / "Dockerfile"
        f.write_text("FROM ubuntu:22.04\nARG REQUIRED_BUILD_ARG\n")
        findings = self.plugin.scan(f)
        finding = next(fi for fi in findings if fi.name == "REQUIRED_BUILD_ARG")
        assert finding.is_required is True

    def test_arg_with_default_is_not_required(self, tmp_path: Path) -> None:
        f = tmp_path / "Dockerfile"
        f.write_text("FROM ubuntu:22.04\nARG OPTIONAL_ARG=mydefault\n")
        findings = self.plugin.scan(f)
        finding = next(fi for fi in findings if fi.name == "OPTIONAL_ARG")
        assert finding.is_required is False

    def test_env_with_value_is_not_required(self, tmp_path: Path) -> None:
        f = tmp_path / "Dockerfile"
        f.write_text("FROM ubuntu:22.04\nENV MY_CONFIG=somevalue\n")
        findings = self.plugin.scan(f)
        finding = next(fi for fi in findings if fi.name == "MY_CONFIG")
        assert finding.is_required is False

    def test_dockerfile_variant_filename(self) -> None:
        assert "Dockerfile.dev" in self.plugin.supported_filenames or \
               any(p.endswith("Dockerfile") for p in self.plugin.supported_filenames)
