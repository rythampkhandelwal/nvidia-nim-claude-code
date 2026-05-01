<div align="center">

# Free Claude Code

Claude Code proxy focused on NVIDIA NIM and direct Claude Code CLI usage.

</div>

## What It Does

- Proxies Anthropic-compatible Claude Code requests to NVIDIA NIM.
- Keeps the app surface centered on direct Claude Code usage.
- Uses one configured NVIDIA NIM model for all Claude Code requests.

## Quick Start

1. Install Python 3.14 and `uv`.
2. Copy `.env.example` to `.env`.
3. Set `NVIDIA_NIM_API_KEY` and `ANTHROPIC_AUTH_TOKEN`.
4. Start the proxy:
5. Install dependency :
```bash
pip install uv
```

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8082
```

5. Point Claude Code at the proxy:

Point `ANTHROPIC_BASE_URL` at the proxy root. Do not append `/v1`.

PowerShell:

```powershell
$env:ANTHROPIC_AUTH_TOKEN="freecc"; $env:ANTHROPIC_BASE_URL="http://localhost:8082"; claude --dangerously-skip-permissions
```

Bash:

```bash
ANTHROPIC_AUTH_TOKEN="freecc" ANTHROPIC_BASE_URL="http://localhost:8082" claude --dangerously-skip-permissions
```

CMD:

```cmd
set ANTHROPIC_AUTH_TOKEN=freecc && set ANTHROPIC_BASE_URL=http://localhost:8082 && claude --dangerously-skip-permissions
```

## Configuration

The main settings live in [`.env.example`](.env.example):

- `NVIDIA_NIM_API_KEY`
- `MODEL`
- `ANTHROPIC_AUTH_TOKEN`
- `CLAUDE_WORKSPACE`
- `ALLOWED_DIR`
- `CLAUDE_CLI_BIN`

## API

The proxy exposes Claude-compatible endpoints such as:

- `/v1/messages`
- `/v1/messages/count_tokens`
- `/v1/models`
- `/health`

## Development

Run the code quality checks with:

```bash
uv run ty check
uv run ruff check
```

## Notes

- The repository is intended for direct Claude Code usage with NVIDIA NIM.

## My suggested .env variables.

- Fill the nvidia_nim_api_key with your api key.
- choose the mdoel as "nvidia_nim/qwen/qwen3-coder-480b-a35b-instruct" for best, fast and reliable response (as per my testings :))
