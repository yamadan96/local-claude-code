"""Tests for config loading and precedence."""

from __future__ import annotations

from pathlib import Path

from lcc.config.loader import load_config
from lcc.config.models import AppConfig, PermissionMode


class TestAppConfig:
    def test_defaults(self) -> None:
        config = AppConfig()
        assert config.model == "qwen2.5-coder:14b"
        assert config.base_url == "http://localhost:11434/v1"
        assert config.api_key == ""
        assert config.permission_mode == PermissionMode.ASK
        assert config.max_input_tokens == 16000
        assert config.max_output_tokens == 2000
        assert config.tool_timeout_seconds == 30
        assert config.allow_outside_cwd is False


class TestConfigLoader:
    def test_defaults_without_any_config_files(self, tmp_path: Path) -> None:
        config = load_config(cwd=str(tmp_path))
        assert config.model == "qwen2.5-coder:14b"
        assert config.base_url == "http://localhost:11434/v1"

    def test_cli_overrides_take_precedence(self, tmp_path: Path) -> None:
        config = load_config(
            cli_overrides={
                "model": "llama3:8b",
                "base_url": "http://localhost:1234/v1",
            },
            cwd=str(tmp_path),
        )
        assert config.model == "llama3:8b"
        assert config.base_url == "http://localhost:1234/v1"

    def test_env_vars_override_defaults(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("LCC_MODEL", "custom-model")
        monkeypatch.setenv("LCC_BASE_URL", "http://custom:9999/v1")
        config = load_config(cwd=str(tmp_path))
        assert config.model == "custom-model"
        assert config.base_url == "http://custom:9999/v1"

    def test_cli_overrides_beat_env_vars(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("LCC_MODEL", "env-model")
        config = load_config(
            cli_overrides={"model": "cli-model"},
            cwd=str(tmp_path),
        )
        assert config.model == "cli-model"

    def test_project_toml_loaded(self, tmp_path: Path) -> None:
        toml_content = 'model = "project-model"\nmax_input_tokens = 8000\n'
        (tmp_path / ".lcc.toml").write_text(toml_content)
        config = load_config(cwd=str(tmp_path))
        assert config.model == "project-model"
        assert config.max_input_tokens == 8000

    def test_env_overrides_project_toml(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / ".lcc.toml").write_text('model = "toml-model"\n')
        monkeypatch.setenv("LCC_MODEL", "env-model")
        config = load_config(cwd=str(tmp_path))
        assert config.model == "env-model"

    def test_permission_mode_coercion(self, tmp_path: Path) -> None:
        config = load_config(
            cli_overrides={"permission_mode": "auto"},
            cwd=str(tmp_path),
        )
        assert config.permission_mode == PermissionMode.AUTO

    def test_int_coercion_from_env(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("LCC_MAX_INPUT_TOKENS", "32000")
        config = load_config(cwd=str(tmp_path))
        assert config.max_input_tokens == 32000

    def test_cwd_set_from_parameter(self, tmp_path: Path) -> None:
        config = load_config(cwd=str(tmp_path))
        assert config.cwd == str(tmp_path)

    def test_unknown_keys_ignored(self, tmp_path: Path) -> None:
        (tmp_path / ".lcc.toml").write_text('unknown_key = "value"\nmodel = "ok"\n')
        config = load_config(cwd=str(tmp_path))
        assert config.model == "ok"
        assert not hasattr(config, "unknown_key")
