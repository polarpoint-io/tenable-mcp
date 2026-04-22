# CLAUDE.md

Claude Code — please read [`AGENTS.md`](AGENTS.md) first. It's the canonical contribution guide for this repo and covers structure, the `@mcp.tool()` pattern, testing conventions, security posture, and the release flow.

## Fast facts

- **Project:** MCP server exposing Tenable.io via pyTenable.
- **Run tests:** `make test`
- **Lint:** `make lint`
- **Run locally:** `make run` (stdio) or `make run-http` (SSE on :8000)
- **Image:** `ghcr.io/polarpoint-io/tenable-mcp:latest` — built/pushed by CI on `main` and tags.
- **Secrets:** never hardcode. Credentials come from `TIO_ACCESS_KEY` and `TIO_SECRET_KEY` env vars at runtime.

## When modifying `server.py`

Follow the `@mcp.tool()` pattern documented in `AGENTS.md` — wrap calls in `_run()` + `_safe_call()`, add a `limit` on list tools, and add a mocked test in `tests/test_tools.py`.

## Updating the CHANGELOG

Any change that would be visible to users of the MCP server (new tool, changed tool signature, changed default behaviour, new env var) needs an entry under `## [Unreleased]` in `CHANGELOG.md`.
