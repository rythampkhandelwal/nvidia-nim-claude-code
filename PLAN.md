# Project Plan

`free-claude-code` is a direct Claude Code proxy focused on NVIDIA NIM.

## Current Scope

- Claude Code CLI and IDE clients connect to the FastAPI proxy.
- The proxy translates Anthropic-compatible requests to NVIDIA NIM.
- The runtime keeps a lightweight CLI session manager for `/stop` support.
- No Discord, Telegram, or other messaging integrations are included.

## Main Modules

- `api/` owns the FastAPI app, routes, runtime lifecycle, and provider wiring.
- `core/` owns shared Anthropic protocol helpers and SSE utilities.
- `providers/` owns NVIDIA NIM transport and provider resolution.
- `cli/` owns package entry points and Claude process/session management.
- `config/` owns settings, provider catalog, and logging.

## Working Rules

- Keep the code path direct and NIM-only.
- Avoid reintroducing messaging adapters or platform bot integrations.
- Preserve Claude Code compatibility at the Anthropic API boundary.
