# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI (ruff + pytest across Python 3.10/3.11/3.12, plus a Docker build job).
- Makefile with common dev targets (`install`, `dev`, `test`, `lint`, `run`, `docker`, ...).

## [0.1.0] - 2026-04-22

### Added
- Initial FastMCP server exposing Tenable.io via pyTenable.
- 23 MCP tools across:
  - Scans: `list_scans`, `get_scan`, `launch_scan`, `get_scan_status`, `get_scan_results`
  - Vulnerabilities: `list_vulnerabilities`, `export_vulnerabilities`
  - Assets: `list_assets`, `get_asset`, `search_assets`, `export_assets`
  - Plugins: `get_plugin_info`, `list_plugin_families`
  - Infrastructure: `list_scanners`, `list_folders`, `list_networks`
  - Agents: `list_agents`, `list_agent_groups`
  - Tags: `list_tag_categories`, `list_tag_values`
  - Policies: `list_scan_templates`, `list_policies`
  - Health: `server_info`
- stdio and HTTP/SSE transports, selected via `TRANSPORT` env var.
- Dockerfile (python:3.12-slim, non-root user) and docker-compose.yml.
- Pytest suite that mocks the Tenable.io client.
- README with Claude Desktop integration snippets.
