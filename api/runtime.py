"""Application runtime composition and lifecycle ownership."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from loguru import logger

from config.settings import Settings, get_settings
from providers.registry import ProviderRegistry

if TYPE_CHECKING:
    from cli.manager import CLISessionManager

_SHUTDOWN_TIMEOUT_S = 5.0


async def best_effort(
    name: str,
    awaitable: Any,
    timeout_s: float = _SHUTDOWN_TIMEOUT_S,
    *,
    log_verbose_errors: bool = False,
) -> None:
    """Run a shutdown step with timeout; never raise to callers."""
    try:
        await asyncio.wait_for(awaitable, timeout=timeout_s)
    except TimeoutError:
        logger.warning("Shutdown step timed out: {} ({}s)", name, timeout_s)
    except Exception as e:
        if log_verbose_errors:
            logger.warning(
                "Shutdown step failed: {}: {}: {}",
                name,
                type(e).__name__,
                e,
            )
        else:
            logger.warning(
                "Shutdown step failed: {}: exc_type={}",
                name,
                type(e).__name__,
            )


def warn_if_process_auth_token(settings: Settings) -> None:
    """Warn when server auth was implicitly inherited from the shell."""
    if settings.uses_process_anthropic_auth_token():
        logger.warning(
            "ANTHROPIC_AUTH_TOKEN is set in the process environment but not in "
            "a configured .env file. The proxy will require that token. Add "
            "ANTHROPIC_AUTH_TOKEN= to .env to disable proxy auth, or set the "
            "same token in .env to make server auth explicit."
        )


@dataclass(slots=True)
class AppRuntime:
    """Own CLI and provider runtime resources."""

    app: FastAPI
    settings: Settings
    _provider_registry: ProviderRegistry | None = field(default=None, init=False)
    cli_manager: CLISessionManager | None = None

    @classmethod
    def for_app(
        cls,
        app: FastAPI,
        settings: Settings | None = None,
    ) -> AppRuntime:
        return cls(app=app, settings=settings or get_settings())

    async def startup(self) -> None:
        logger.info("Starting Claude Code Proxy...")
        self._provider_registry = ProviderRegistry()
        self.app.state.provider_registry = self._provider_registry
        warn_if_process_auth_token(self.settings)
        await self._start_cli_manager_if_configured()
        self._publish_state()

    async def shutdown(self) -> None:
        verbose = self.settings.log_api_error_tracebacks
        logger.info("Shutdown requested, cleaning up...")
        if self.cli_manager:
            await best_effort(
                "cli_manager.stop_all",
                self.cli_manager.stop_all(),
                log_verbose_errors=verbose,
            )
        if self._provider_registry is not None:
            await best_effort(
                "provider_registry.cleanup",
                self._provider_registry.cleanup(),
                log_verbose_errors=verbose,
            )
        logger.info("Server shut down cleanly")

    async def _start_cli_manager_if_configured(self) -> None:
        from cli.manager import CLISessionManager

        workspace = (
            os.path.abspath(self.settings.allowed_dir)
            if self.settings.allowed_dir
            else os.getcwd()
        )
        os.makedirs(workspace, exist_ok=True)

        data_path = os.path.abspath(self.settings.claude_workspace)
        os.makedirs(data_path, exist_ok=True)

        api_url = f"http://{self.settings.host}:{self.settings.port}/v1"
        allowed_dirs = [workspace] if self.settings.allowed_dir else []
        plans_dir_abs = os.path.abspath(
            os.path.join(self.settings.claude_workspace, "plans")
        )
        plans_directory = os.path.relpath(plans_dir_abs, workspace)
        self.cli_manager = CLISessionManager(
            workspace_path=workspace,
            api_url=api_url,
            allowed_dirs=allowed_dirs,
            plans_directory=plans_directory,
            claude_bin=self.settings.claude_cli_bin,
            log_raw_cli_diagnostics=self.settings.log_raw_cli_diagnostics,
            log_cli_error_details=False,
        )

    def _publish_state(self) -> None:
        self.app.state.cli_manager = self.cli_manager
