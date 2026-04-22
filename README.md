# pytenable-mcp

A Model Context Protocol (MCP) server that exposes [Tenable.io](https://www.tenable.com/products/tenable-io) to LLM clients (Claude Desktop, Claude Code, Cursor, etc.) via the official [pyTenable](https://github.com/tenable/pyTenable) SDK.

The server surfaces scans, vulnerabilities, assets, plugins, scanners, agents, tags and more as MCP tools — so an LLM can answer questions like "which of our assets have a critical CVE disclosed in the last 30 days?" without you having to manually pull data from the Tenable UI.

## Features

Tools exposed via MCP:

- **Scans** — `list_scans`, `get_scan`, `launch_scan`, `get_scan_status`, `get_scan_results`
- **Vulnerabilities** — `list_vulnerabilities` (workbench), `export_vulnerabilities` (export API)
- **Assets** — `list_assets`, `get_asset`, `search_assets`, `export_assets`
- **Plugins** — `get_plugin_info`, `list_plugin_families`
- **Infrastructure** — `list_scanners`, `list_folders`, `list_networks`
- **Agents** — `list_agents`, `list_agent_groups`
- **Tags** — `list_tag_categories`, `list_tag_values`
- **Policies / templates** — `list_scan_templates`, `list_policies`
- **Health** — `server_info`

Transports: stdio (default, ideal for local/Docker integrations) and HTTP/SSE (for remote use).

## Requirements

- Python 3.10+
- Tenable.io account with API keys (Settings → My Account → API Keys)
- Docker (optional, for containerised use)

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Required | Description |
|----------|----------|-------------|
| `TIO_ACCESS_KEY` | yes | Tenable.io API access key |
| `TIO_SECRET_KEY` | yes | Tenable.io API secret key |
| `TIO_URL` | no | API base URL (default `https://cloud.tenable.com`) |
| `TRANSPORT` | no | `stdio` (default) or `http` |
| `HTTP_HOST` | no | Bind host when `TRANSPORT=http` (default `0.0.0.0`) |
| `HTTP_PORT` | no | Bind port when `TRANSPORT=http` (default `8000`) |
| `LOG_LEVEL` | no | Python log level (default `INFO`) |

## Local install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

export TIO_ACCESS_KEY=...
export TIO_SECRET_KEY=...

# stdio (for MCP clients)
pytenable-mcp

# HTTP/SSE
TRANSPORT=http HTTP_PORT=8000 pytenable-mcp
```

## Docker

### Build

```bash
docker build -t pytenable-mcp:latest .
```

### Run (HTTP/SSE, default in compose)

```bash
export TIO_ACCESS_KEY=...
export TIO_SECRET_KEY=...
docker compose up -d
# MCP SSE endpoint: http://localhost:8000/sse
```

### Run (stdio — one-shot)

Most MCP clients will launch the container themselves via `docker run -i`. Example:

```bash
docker run --rm -i \
  -e TIO_ACCESS_KEY \
  -e TIO_SECRET_KEY \
  pytenable-mcp:latest
```

## Claude Desktop integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent on your platform:

```json
{
  "mcpServers": {
    "tenable": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "TIO_ACCESS_KEY",
        "-e", "TIO_SECRET_KEY",
        "pytenable-mcp:latest"
      ],
      "env": {
        "TIO_ACCESS_KEY": "your_access_key",
        "TIO_SECRET_KEY": "your_secret_key"
      }
    }
  }
}
```

Or, if installed locally as a Python package:

```json
{
  "mcpServers": {
    "tenable": {
      "command": "pytenable-mcp",
      "env": {
        "TIO_ACCESS_KEY": "your_access_key",
        "TIO_SECRET_KEY": "your_secret_key"
      }
    }
  }
}
```

## Development

```bash
pip install -e .[dev]
pytest
ruff check src tests
```

## Security notes

- The server runs as a non-root user inside the container.
- API keys are read from environment variables only — no on-disk secret storage by default.
- No write operations are exposed beyond `launch_scan`; destructive actions (delete, update config) are deliberately omitted. Add new tools with care.
- Tenable.io rate limits still apply; the `limit` argument on list-style tools exists to keep responses bounded.

## License

MIT — see [LICENSE](LICENSE).
