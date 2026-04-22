# AGENTS.md

Guidance for AI coding agents (Claude Code, Cursor, Copilot, Aider, etc.) and human contributors working in this repository.

This file follows the emerging [AGENTS.md](https://agentsmd.net/) convention. It takes precedence over generic instructions the agent may have learned; when a user's explicit instruction conflicts with this file, the user wins.

## TL;DR for an agent opening this repo

- **What it is:** a Model Context Protocol (MCP) server that wraps [pyTenable](https://github.com/tenable/pyTenable) so LLMs can query Tenable.io.
- **Language:** Python 3.10+.
- **MCP SDK:** the official `mcp` package, using `FastMCP`.
- **Transports:** stdio (default) and HTTP/SSE — selected via `TRANSPORT` env var.
- **Deploy target:** a Docker image published to `ghcr.io/polarpoint-io/tenable-mcp`.
- **No secrets in repo.** Credentials come from `TIO_ACCESS_KEY` / `TIO_SECRET_KEY` at runtime only.

## Repository layout

```
.
├── src/pytenable_mcp/
│   ├── __init__.py
│   ├── __main__.py        # `python -m pytenable_mcp`
│   ├── client.py          # lazy, env-driven pyTenable client factory
│   └── server.py          # all @mcp.tool() definitions + entrypoint
├── tests/
│   └── test_tools.py      # pytest + unittest.mock; mocks get_client()
├── .github/workflows/
│   └── ci.yml             # ruff + pytest + Docker build/push to GHCR
├── Dockerfile             # python:3.12-slim, non-root user
├── docker-compose.yml     # local HTTP/SSE run
├── pyproject.toml         # setuptools, deps, ruff config
├── Makefile               # install/dev/test/lint/run/docker targets
├── push-to-github.sh      # one-shot helper to push to github.com
├── README.md              # user-facing docs
├── AGENTS.md              # this file
├── CLAUDE.md              # pointer for Claude Code
├── CHANGELOG.md           # Keep-a-Changelog format
└── LICENSE                # MIT
```

## Dev loop

```bash
make dev      # pip install -e .[dev]
make test     # pytest -q
make lint     # ruff check src tests
make format   # ruff check --fix
make run      # run the server on stdio
make run-http # run on HTTP/SSE, port 8000
```

Don't invoke git hooks or `make docker` as part of routine dev work — CI handles the image build/push.

## Adding a new MCP tool

The canonical pattern in `src/pytenable_mcp/server.py`:

```python
@mcp.tool()
def list_foos(filter_bar: str | None = None, limit: int = 100) -> dict:
    """One-line description (shown to the LLM).

    Args:
        filter_bar: Plain-English explanation of this arg.
        limit: Maximum items to return.
    """
    def _run() -> dict:
        tio = get_client()
        items: list[dict] = []
        for item in tio.foos.list(filter=filter_bar):
            items.append(item)
            if len(items) >= limit:
                break
        return {"count": len(items), "items": _jsonable(items)}

    return _safe_call(_run)
```

Conventions:

1. **Wrap the call in `_run()` and return via `_safe_call(_run)`.** This turns pyTenable exceptions into `{"error": "...", "message": "..."}` so the LLM can react rather than the whole call blowing up.
2. **Pass JSON through `_jsonable()`** if the response includes anything pyTenable returns as e.g. `datetime` — it stringifies non-JSON types.
3. **Add a `limit` arg** on list-style tools. LLMs love to ask for everything; put an upper bound so you don't hammer the API.
4. **Prefer explicit args over `**kwargs`.** The LLM reads the signature to decide how to call the tool; undocumented kwargs aren't discoverable.
5. **Docstring first line == tool description.** Keep it short and concrete. The LLM picks tools by description.
6. **Never expose a destructive operation** (delete, overwrite, permission change) without gating it behind an env flag like `TIO_ENABLE_WRITE=1`. The LLM will absolutely call `delete_all_scans()` if you let it.
7. **Add a test** to `tests/test_tools.py` that mocks `get_client` and asserts the tool produces the expected shape for both success and error paths.

## Testing convention

Tests use `unittest.mock.patch("pytenable_mcp.server.get_client")` so no network or real credentials are needed:

```python
@patch("pytenable_mcp.server.get_client")
def test_list_foos(get_client):
    foos = MagicMock()
    foos.list.return_value = iter([{"id": 1}])
    get_client.return_value = MagicMock(foos=foos)

    result = server.list_foos()
    assert result["count"] == 1
```

Call the tool function directly (e.g. `server.list_foos()`). **Do not** use `.fn` — FastMCP's `@tool()` decorator returns the function unchanged in `mcp>=1.2`.

## Coding style

- Python 3.10+ features are fine (`X | Y` unions, `match`, `dict[str, Any]` generics).
- `from __future__ import annotations` at the top of every module. Type hints cost zero runtime.
- Line length: 100 (ruff-enforced).
- No trailing whitespace, no tabs.
- Prefer `pathlib.Path` over string path manipulation.
- Logging via `logger = logging.getLogger("pytenable_mcp")`; don't use `print()`.
- Docstrings: short imperative summary line, then an `Args:` block when the tool takes parameters.

## Security posture

This server talks to a sensitive security system. Keep it that way:

- **Never log secrets.** `TIO_ACCESS_KEY` and `TIO_SECRET_KEY` must stay out of logs, stack traces, and tool output.
- **Read-only by default.** `launch_scan` is the only non-read tool and is already documented. Any new write operation requires an explicit flag (`TIO_ENABLE_WRITE=1`) and a clear mention in `README.md`.
- **No persistent state.** The container has no volumes and no on-disk cache; the pyTenable client is memoised in-process only.
- **Dependencies.** Pin majors via `pyproject.toml`. When adding a dep, justify it in the commit message.

## Release flow

1. Bump version in `pyproject.toml` and `src/pytenable_mcp/__init__.py`.
2. Update `CHANGELOG.md` (`## [x.y.z] - YYYY-MM-DD`).
3. Commit, tag `vX.Y.Z`, push the tag — CI will build and push `ghcr.io/polarpoint-io/tenable-mcp:X.Y.Z`, `:X.Y`, and retag `:latest` on `main`.

## What to do when things are unclear

- Read [`README.md`](README.md) for the user-facing contract.
- Check `CHANGELOG.md` for recent changes.
- Grep for existing patterns before inventing new ones — there are usually 20+ examples already in `server.py`.
- If a pyTenable method doesn't behave as documented, check the [pyTenable source](https://github.com/tenable/pyTenable) directly; the docs occasionally lag.

## Non-goals

- This project is deliberately **not** a full Tenable.io admin console. It won't ever manage users, billing, or org-level config.
- It doesn't cache results. Freshness is more valuable than speed for security data.
- It doesn't try to wrap Tenable.sc (Security Center), Tenable OT, or Nessus Pro. Separate projects if needed.
