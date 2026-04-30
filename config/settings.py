"""Centralized configuration using Pydantic Settings."""

import os
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import HTTP_CONNECT_TIMEOUT_DEFAULT
from .nim import NimSettings
from .provider_ids import SUPPORTED_PROVIDER_IDS


def _env_files() -> tuple[Path, ...]:
    """Return env file paths in priority order (later overrides earlier)."""
    files: list[Path] = [
        Path.home() / ".config" / "free-claude-code" / ".env",
        Path(".env"),
    ]
    if explicit := os.environ.get("FCC_ENV_FILE"):
        files.append(Path(explicit))
    return tuple(files)


def _configured_env_files(model_config: Mapping[str, Any]) -> tuple[Path, ...]:
    """Return the currently configured env files for Settings."""
    configured = model_config.get("env_file")
    if configured is None:
        return ()
    if isinstance(configured, (str, Path)):
        return (Path(configured),)
    return tuple(Path(item) for item in configured)


def _env_file_contains_key(path: Path, key: str) -> bool:
    """Check whether a dotenv-style file defines the given key."""
    return _env_file_value(path, key) is not None


def _env_file_value(path: Path, key: str) -> str | None:
    """Return a dotenv value when the file explicitly defines the key."""
    if not path.is_file():
        return None

    try:
        values = dotenv_values(path)
    except OSError:
        return None

    if key not in values:
        return None
    value = values[key]
    return "" if value is None else value


def _env_file_override(model_config: Mapping[str, Any], key: str) -> str | None:
    """Return the last configured dotenv value that explicitly defines a key."""
    configured_value: str | None = None
    for env_file in _configured_env_files(model_config):
        value = _env_file_value(env_file, key)
        if value is not None:
            configured_value = value
    return configured_value


def _removed_env_var_message(model_config: Mapping[str, Any]) -> str | None:
    """Return a migration error for removed env vars, if present."""
    removed_keys = ("NIM_ENABLE_THINKING", "ENABLE_THINKING")
    replacement = "ENABLE_MODEL_THINKING"

    for removed_key in removed_keys:
        if removed_key in os.environ:
            return (
                f"{removed_key} has been removed in this release. "
                f"Rename it to {replacement}."
            )

        for env_file in _configured_env_files(model_config):
            if _env_file_contains_key(env_file, removed_key):
                return (
                    f"{removed_key} has been removed in this release. "
                    f"Rename it to {replacement}. Found in {env_file}."
                )

    return None


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ==================== NVIDIA NIM Config ====================
    nvidia_nim_api_key: str = ""

    # ==================== Model ====================
    # All Claude model requests are mapped to this single model.
    # Format: provider_type/model/name
    model: str = "nvidia_nim/z-ai/glm4.7"

    # ==================== Per-Provider Proxy ====================
    nvidia_nim_proxy: str = Field(default="", validation_alias="NVIDIA_NIM_PROXY")

    # ==================== Provider Rate Limiting ====================
    provider_rate_limit: int = Field(default=40, validation_alias="PROVIDER_RATE_LIMIT")
    provider_rate_window: int = Field(
        default=60, validation_alias="PROVIDER_RATE_WINDOW"
    )
    provider_max_concurrency: int = Field(
        default=5, validation_alias="PROVIDER_MAX_CONCURRENCY"
    )
    enable_model_thinking: bool = Field(
        default=True, validation_alias="ENABLE_MODEL_THINKING"
    )

    # ==================== HTTP Client Timeouts ====================
    http_read_timeout: float = Field(
        default=120.0, validation_alias="HTTP_READ_TIMEOUT"
    )
    http_write_timeout: float = Field(
        default=10.0, validation_alias="HTTP_WRITE_TIMEOUT"
    )
    http_connect_timeout: float = Field(
        default=HTTP_CONNECT_TIMEOUT_DEFAULT,
        validation_alias="HTTP_CONNECT_TIMEOUT",
    )

    # ==================== Fast Prefix Detection ====================
    fast_prefix_detection: bool = True

    # ==================== Optimizations ====================
    enable_network_probe_mock: bool = True
    enable_title_generation_skip: bool = True
    enable_suggestion_mode_skip: bool = True
    enable_filepath_extraction_mock: bool = True

    # ==================== Local web server tools (web_search / web_fetch) ====================
    # Off by default: these tools perform outbound HTTP from the proxy (SSRF risk).
    enable_web_server_tools: bool = Field(
        default=False, validation_alias="ENABLE_WEB_SERVER_TOOLS"
    )
    # Comma-separated URL schemes allowed for web_fetch (default: http,https).
    web_fetch_allowed_schemes: str = Field(
        default="http,https", validation_alias="WEB_FETCH_ALLOWED_SCHEMES"
    )
    # When true, skip private/loopback/link-local IP blocking for web_fetch (lab only).
    web_fetch_allow_private_networks: bool = Field(
        default=False, validation_alias="WEB_FETCH_ALLOW_PRIVATE_NETWORKS"
    )

    # ==================== Debug / diagnostic logging (avoid sensitive content) ====================
    # When false (default), API and SSE helpers log only metadata (counts, lengths, ids).
    log_raw_api_payloads: bool = Field(
        default=False, validation_alias="LOG_RAW_API_PAYLOADS"
    )
    log_raw_sse_events: bool = Field(
        default=False, validation_alias="LOG_RAW_SSE_EVENTS"
    )
    # When false (default), unhandled exceptions log only type + route metadata (no message/traceback).
    log_api_error_tracebacks: bool = Field(
        default=False, validation_alias="LOG_API_ERROR_TRACEBACKS"
    )
    # When true, log full Claude CLI stderr, non-JSON lines, and parser error text.
    log_raw_cli_diagnostics: bool = Field(
        default=False, validation_alias="LOG_RAW_CLI_DIAGNOSTICS"
    )

    # ==================== NIM Settings ====================
    nim: NimSettings = Field(default_factory=NimSettings)

    claude_workspace: str = "./agent_workspace"
    allowed_dir: str = ""
    claude_cli_bin: str = Field(default="claude", validation_alias="CLAUDE_CLI_BIN")

    # ==================== Server ====================
    host: str = "0.0.0.0"
    port: int = 8082
    log_file: str = "server.log"
    # Optional server API key to protect endpoints (Anthropic-style)
    # Set via env `ANTHROPIC_AUTH_TOKEN`. When empty, no auth is required.
    anthropic_auth_token: str = Field(
        default="", validation_alias="ANTHROPIC_AUTH_TOKEN"
    )

    @model_validator(mode="before")
    @classmethod
    def reject_removed_env_vars(cls, data: Any) -> Any:
        """Fail fast when removed environment variables are still configured."""
        if message := _removed_env_var_message(cls.model_config):
            raise ValueError(message)
        return data

    @field_validator("web_fetch_allowed_schemes")
    @classmethod
    def validate_web_fetch_allowed_schemes(cls, v: str) -> str:
        schemes = [part.strip().lower() for part in v.split(",") if part.strip()]
        if not schemes:
            raise ValueError("web_fetch_allowed_schemes must list at least one scheme")
        for scheme in schemes:
            if not scheme.isascii() or not scheme.isalpha():
                raise ValueError(
                    f"Invalid URL scheme in web_fetch_allowed_schemes: {scheme!r}"
                )
        return ",".join(schemes)

    @field_validator("model")
    @classmethod
    def validate_model_format(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if "/" not in v:
            raise ValueError(
                f"Model must be prefixed with provider type. "
                f"Valid providers: {', '.join(SUPPORTED_PROVIDER_IDS)}. "
                f"Format: provider_type/model/name"
            )
        provider = v.split("/", 1)[0]
        if provider not in SUPPORTED_PROVIDER_IDS:
            supported = ", ".join(f"'{p}'" for p in SUPPORTED_PROVIDER_IDS)
            raise ValueError(f"Invalid provider: '{provider}'. Supported: {supported}")
        return v

    @model_validator(mode="after")
    def prefer_dotenv_anthropic_auth_token(self) -> Settings:
        """Let explicit .env auth config override stale shell/client tokens."""
        dotenv_value = _env_file_override(self.model_config, "ANTHROPIC_AUTH_TOKEN")
        if dotenv_value is not None:
            self.anthropic_auth_token = dotenv_value
        return self

    def uses_process_anthropic_auth_token(self) -> bool:
        """Return whether proxy auth came from process env, not dotenv config."""
        if _env_file_override(self.model_config, "ANTHROPIC_AUTH_TOKEN") is not None:
            return False
        return bool(os.environ.get("ANTHROPIC_AUTH_TOKEN"))

    @property
    def provider_type(self) -> str:
        """Return the only supported provider type."""
        return "nvidia_nim"

    @property
    def model_name(self) -> str:
        """Extract the actual model name from the default model string."""
        return Settings.parse_model_name(self.model)

    def resolve_model(self, claude_model_name: str) -> str:
        """Resolve any Claude model name to the configured NVIDIA NIM model."""
        return self.model

    def resolve_thinking(self, claude_model_name: str) -> bool:
        """Resolve whether thinking is enabled for an incoming Claude model name."""
        return self.enable_model_thinking

    def web_fetch_allowed_scheme_set(self) -> frozenset[str]:
        """Return normalized schemes allowed for web_fetch."""
        return frozenset(
            part.strip().lower()
            for part in self.web_fetch_allowed_schemes.split(",")
            if part.strip()
        )

    @staticmethod
    def parse_provider_type(model_string: str) -> str:
        """Extract provider type from any 'provider/model' string."""
        return model_string.split("/", 1)[0]

    @staticmethod
    def parse_model_name(model_string: str) -> str:
        """Extract model name from any 'provider/model' string."""
        return model_string.split("/", 1)[1]

    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
