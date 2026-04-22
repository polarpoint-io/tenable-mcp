# tenable-mcp

A Model Context Protocol (MCP) server that exposes [Tenable.io](https://www.tenable.com/products/tenable-io) to LLM clients (Claude Desktop, Claude Code, Cursor, VS Code, etc.) via the official [pyTenable](https://github.com/tenable/pyTenable) SDK.

Ask an LLM things like "which of our assets have a critical CVE disclosed in the last 30 days?", "summarise the latest scan for the production network", or "launch the quarterly compliance scan against 10.0.0.0/24" — and the LLM can answer by calling Tenable.io directly through this server.

> **Image**: `ghcr.io/polarpoint-io/tenable-mcp:latest`
> **Repo**: https://github.com/polarpoint-io/tenable-mcp

## Table of contents

- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Client integrations](#client-integrations)
  - [Claude Desktop](#claude-desktop)
  - [Claude Code](#claude-code)
  - [Cursor](#cursor)
  - [VS Code (Continue)](#vs-code-continue)
- [Tool reference](#tool-reference)
- [Example prompts](#example-prompts)
- [Running from source](#running-from-source)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Security notes](#security-notes)

## Quick start

Pull the prebuilt image and run it in stdio mode from any MCP-capable client:

```bash
docker pull ghcr.io/polarpoint-io/tenable-mcp:latest

docker run --rm -i \
  -e TIO_ACCESS_KEY=your_access_key \
  -e TIO_SECRET_KEY=your_secret_key \
  ghcr.io/polarpoint-io/tenable-mcp:latest
```

Or run it as a standalone HTTP/SSE service:

```bash
docker run --rm \
  -p 8000:8000 \
  -e TIO_ACCESS_KEY=your_access_key \
  -e TIO_SECRET_KEY=your_secret_key \
  -e TRANSPORT=http \
  ghcr.io/polarpoint-io/tenable-mcp:latest
# SSE endpoint: http://localhost:8000/sse
```

Get your keys from Tenable.io: **Settings → My Account → API Keys**.

## Configuration

All configuration is via environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TIO_ACCESS_KEY` | yes | — | Tenable.io API access key |
| `TIO_SECRET_KEY` | yes | — | Tenable.io API secret key |
| `TIO_URL` | no | `https://cloud.tenable.com` | API base URL |
| `TRANSPORT` | no | `stdio` | `stdio` or `http` |
| `HTTP_HOST` | no | `0.0.0.0` | Bind host (HTTP mode) |
| `HTTP_PORT` | no | `8000` | Bind port (HTTP mode) |
| `LOG_LEVEL` | no | `INFO` | Python log level |

See [`.env.example`](.env.example) for a copy-pasteable template.

## Client integrations

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent on your platform:

```json
{
  "mcpServers": {
    "tenable": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "TIO_ACCESS_KEY",
        "-e", "TIO_SECRET_KEY",
        "ghcr.io/polarpoint-io/tenable-mcp:latest"
      ],
      "env": {
        "TIO_ACCESS_KEY": "your_access_key",
        "TIO_SECRET_KEY": "your_secret_key"
      }
    }
  }
}
```

Restart Claude Desktop. You should see a hammer icon in the chat indicating the `tenable` server is connected, with all 23 tools available.

### Claude Code

Add the server to your project with the `claude mcp add` command:

```bash
claude mcp add tenable -- docker run --rm -i \
  -e TIO_ACCESS_KEY \
  -e TIO_SECRET_KEY \
  ghcr.io/polarpoint-io/tenable-mcp:latest
```

Then export your keys before running `claude`:

```bash
export TIO_ACCESS_KEY=your_access_key
export TIO_SECRET_KEY=your_secret_key
```

### Cursor

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "tenable": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "-e", "TIO_ACCESS_KEY", "-e", "TIO_SECRET_KEY", "ghcr.io/polarpoint-io/tenable-mcp:latest"],
      "env": {
        "TIO_ACCESS_KEY": "your_access_key",
        "TIO_SECRET_KEY": "your_secret_key"
      }
    }
  }
}
```

### VS Code (Continue)

Add to `~/.continue/config.json`:

```json
{
  "mcpServers": [
    {
      "name": "tenable",
      "command": "docker",
      "args": ["run", "--rm", "-i", "-e", "TIO_ACCESS_KEY", "-e", "TIO_SECRET_KEY", "ghcr.io/polarpoint-io/tenable-mcp:latest"],
      "env": {
        "TIO_ACCESS_KEY": "your_access_key",
        "TIO_SECRET_KEY": "your_secret_key"
      }
    }
  ]
}
```

## Tool reference

The server exposes 23 tools, grouped by capability. All return JSON. Errors from the Tenable API are caught and returned as `{"error": "...", "message": "..."}` rather than raised, so the LLM can handle them gracefully.

### Scans

| Tool | Description |
|------|-------------|
| `list_scans` | List scans (optional folder / last-modified filters) |
| `get_scan` | Full details of a single scan (incl. hosts, info) |
| `launch_scan` | Launch a scan; optional target override |
| `get_scan_status` | Current run status (running / completed / canceled) |
| `get_scan_results` | Summarised host + severity counts |

### Vulnerabilities

| Tool | Description |
|------|-------------|
| `list_vulnerabilities` | Workbench query with severity / plugin / CVE filters |
| `export_vulnerabilities` | Export-API stream of findings |

### Assets

| Tool | Description |
|------|-------------|
| `list_assets` | List assets via workbenches |
| `get_asset` | Full details for an asset UUID |
| `search_assets` | Filter by hostname / IPv4 / tag |
| `export_assets` | Export-API stream of assets |

### Plugins

| Tool | Description |
|------|-------------|
| `get_plugin_info` | Full plugin metadata (description, solution, CVEs, CVSS) |
| `list_plugin_families` | Plugin families and their counts |

### Infrastructure

| Tool | Description |
|------|-------------|
| `list_scanners` | Cloud + on-prem scanners |
| `list_folders` | Scan folders |
| `list_networks` | Logical network segments |

### Agents

| Tool | Description |
|------|-------------|
| `list_agents` | Connected Nessus agents |
| `list_agent_groups` | Agent groups |

### Tags

| Tool | Description |
|------|-------------|
| `list_tag_categories` | All tag categories |
| `list_tag_values` | Tag values, optionally filtered by category |

### Policies

| Tool | Description |
|------|-------------|
| `list_scan_templates` | Available scan templates |
| `list_policies` | User-defined scan policies |

### Health

| Tool | Description |
|------|-------------|
| `server_info` | Connected-tenant metadata (session + server properties) |

## Example prompts

Once the server is connected, try:

> **Triage:** "Show me every critical-severity finding discovered in the last 7 days, grouped by plugin."
>
> **Asset context:** "What's the patch posture of hostname `web-01.prod`?"
>
> **Scan operations:** "Launch the 'Weekly PCI Scan' against 10.10.0.0/16 and tell me when it's done."
>
> **Plugin lookup:** "Explain plugin 19506 — what does it actually check for?"
>
> **Change analysis:** "Diff the most recent two runs of the 'DMZ scan' — what new vulns appeared?"
>
> **Inventory:** "How many Linux servers are we currently monitoring, broken down by tag value for `environment`?"

The LLM will pick the appropriate tool(s), chain them as needed, and summarise results.

## Running from source

```bash
git clone git@github.com:polarpoint-io/tenable-mcp.git
cd tenable-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]

export TIO_ACCESS_KEY=...
export TIO_SECRET_KEY=...

pytenable-mcp                                    # stdio
TRANSPORT=http HTTP_PORT=8000 pytenable-mcp      # HTTP/SSE
```

Or with the Makefile:

```bash
make dev      # install with dev extras
make test     # pytest
make lint     # ruff check
make run      # stdio
make run-http # HTTP/SSE on :8000
make docker   # build the image locally
```

## Development

```bash
make dev
make test
make lint
```

Adding a new tool is a matter of:

1. Wrap a `pyTenable` method in a `_run()` closure inside a new `@mcp.tool()` function in `src/pytenable_mcp/server.py`.
2. Use `_safe_call()` to make pyTenable exceptions serialise cleanly for the LLM.
3. Add a mocked-client test in `tests/test_tools.py`.

See [`AGENTS.md`](AGENTS.md) for deeper contribution guidance (aimed at both humans and AI coding agents).

## Troubleshooting

- **`TIO_ACCESS_KEY required`** — your env vars aren't reaching the container. For `docker run -e FOO` to forward, `FOO` has to be set in the calling shell.
- **`401 Unauthorized` from Tenable** — the key is wrong, or lacks the needed permission. Create a new key pair in Tenable.io and make sure your user role has read access to the resources you're querying.
- **Empty results for `list_agents`** — `scanner_id` defaults to `1` (the cloud scanner). For on-prem scanners, pass the scanner's real ID (get it from `list_scanners`).
- **Claude Desktop doesn't see the server** — check the logs at `~/Library/Logs/Claude/mcp*.log` (macOS); the most common issue is a typo in the JSON or Docker not being on PATH.
- **Rate limiting** — Tenable.io rate-limits the API. The `limit` argument on list-style tools exists so an over-eager LLM doesn't hammer it.

## Security notes

- The container runs as a non-root user.
- API keys are read from env vars only — no on-disk storage by default.
- Destructive operations (delete scan, update policy, change permissions, etc.) are deliberately **not** exposed. Only `launch_scan` is non-read.
- If you add write tools, consider guarding them behind a separate env flag (`TIO_ENABLE_WRITE=1`) so accidental LLM calls are prevented.

## License

MIT — see [LICENSE](LICENSE).
