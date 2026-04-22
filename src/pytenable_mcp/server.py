"""FastMCP server exposing Tenable.io via pyTenable.

Tools provided:
    - list_scans / get_scan / launch_scan / get_scan_status / get_scan_results
    - list_vulnerabilities / export_vulnerabilities
    - list_assets / get_asset / search_assets

Transport selection (env vars):
    TRANSPORT=stdio (default)   - MCP stdio transport
    TRANSPORT=http              - SSE/HTTP transport on HTTP_HOST:HTTP_PORT
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import TenableConfigError, get_client

logger = logging.getLogger("pytenable_mcp")

mcp = FastMCP(
    name="pytenable-mcp",
    instructions=(
        "Query Tenable.io for scans, assets, and vulnerabilities. "
        "Requires TIO_ACCESS_KEY and TIO_SECRET_KEY env vars."
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_call(fn, *args, **kwargs) -> Any:
    """Wrap pyTenable calls so credential errors surface cleanly to the LLM."""
    try:
        return fn(*args, **kwargs)
    except TenableConfigError as exc:
        return {"error": "configuration", "message": str(exc)}
    except Exception as exc:  # noqa: BLE001 - surface all upstream errors
        logger.exception("Tenable.io call failed")
        return {"error": exc.__class__.__name__, "message": str(exc)}


def _jsonable(obj: Any) -> Any:
    """Best-effort conversion of pyTenable responses to JSON-safe types."""
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return json.loads(json.dumps(obj, default=str))


# ---------------------------------------------------------------------------
# Scans
# ---------------------------------------------------------------------------

@mcp.tool()
def list_scans(folder_id: int | None = None, last_modified_after: int | None = None) -> dict:
    """List scans configured in Tenable.io.

    Args:
        folder_id: Optional folder ID to filter by.
        last_modified_after: Unix timestamp; only return scans modified after this time.
    """
    def _run() -> dict:
        tio = get_client()
        kwargs: dict[str, Any] = {}
        if folder_id is not None:
            kwargs["folder_id"] = folder_id
        if last_modified_after is not None:
            kwargs["last_modified"] = last_modified_after
        scans = list(tio.scans.list(**kwargs))
        return {"count": len(scans), "scans": _jsonable(scans)}

    return _safe_call(_run)


@mcp.tool()
def get_scan(scan_id: int, history_id: int | None = None) -> dict:
    """Get full details for a single scan, including hosts and info.

    Args:
        scan_id: Tenable scan ID.
        history_id: Optional historical run ID.
    """
    def _run() -> dict:
        tio = get_client()
        details = tio.scans.details(scan_id, history_id=history_id)
        return _jsonable(details)

    return _safe_call(_run)


@mcp.tool()
def launch_scan(scan_id: int, targets: list[str] | None = None) -> dict:
    """Launch an existing scan. Optionally override the target list for this run.

    Args:
        scan_id: Tenable scan ID.
        targets: Optional list of targets (hostnames / IPs / CIDRs) to scan.
    """
    def _run() -> dict:
        tio = get_client()
        scan_uuid = tio.scans.launch(scan_id, targets=targets)
        return {"scan_id": scan_id, "scan_uuid": scan_uuid}

    return _safe_call(_run)


@mcp.tool()
def get_scan_status(scan_id: int, history_id: int | None = None) -> dict:
    """Return the run status of a scan (e.g. running, completed, canceled)."""
    def _run() -> dict:
        tio = get_client()
        status = tio.scans.status(scan_id, history_id=history_id)
        return {"scan_id": scan_id, "status": status}

    return _safe_call(_run)


@mcp.tool()
def get_scan_results(scan_id: int, history_id: int | None = None, limit: int = 50) -> dict:
    """Summarise scan results: top hosts and vulnerability counts.

    Args:
        scan_id: Tenable scan ID.
        history_id: Optional historical run ID.
        limit: Maximum number of hosts to include (default 50).
    """
    def _run() -> dict:
        tio = get_client()
        details = tio.scans.details(scan_id, history_id=history_id)
        hosts = (details.get("hosts") or [])[:limit]
        info = details.get("info", {})
        return _jsonable(
            {
                "scan_id": scan_id,
                "name": info.get("name"),
                "status": info.get("status"),
                "hostcount": info.get("hostcount"),
                "vulnerability_counts": {
                    "critical": sum(h.get("critical", 0) for h in hosts),
                    "high": sum(h.get("high", 0) for h in hosts),
                    "medium": sum(h.get("medium", 0) for h in hosts),
                    "low": sum(h.get("low", 0) for h in hosts),
                    "info": sum(h.get("info", 0) for h in hosts),
                },
                "hosts": hosts,
            }
        )

    return _safe_call(_run)


# ---------------------------------------------------------------------------
# Vulnerabilities
# ---------------------------------------------------------------------------

@mcp.tool()
def list_vulnerabilities(
    severity: list[str] | None = None,
    plugin_id: int | None = None,
    cve: str | None = None,
    limit: int = 100,
) -> dict:
    """Query Tenable.io vulnerabilities workbench.

    Args:
        severity: Filter by severity list, e.g. ["critical", "high"].
        plugin_id: Only return findings for this Nessus plugin ID.
        cve: Filter to a specific CVE identifier, e.g. "CVE-2024-12345".
        limit: Maximum number of findings to return (default 100).
    """
    def _run() -> dict:
        tio = get_client()
        filters: list[tuple[str, str, str]] = []
        if severity:
            filters.append(("severity", "eq", ",".join(severity)))
        if plugin_id is not None:
            filters.append(("plugin.id", "eq", str(plugin_id)))
        if cve:
            filters.append(("plugin.cve", "eq", cve))

        findings: list[dict] = []
        iterator = tio.workbenches.vulns(*filters) if filters else tio.workbenches.vulns()
        for item in iterator:
            findings.append(item)
            if len(findings) >= limit:
                break
        return {"count": len(findings), "findings": _jsonable(findings)}

    return _safe_call(_run)


@mcp.tool()
def export_vulnerabilities(
    severity: list[str] | None = None,
    since: int | None = None,
    limit: int = 500,
) -> dict:
    """Stream findings from the vulnerability export API.

    Args:
        severity: Severity filter, e.g. ["critical", "high"].
        since: Unix timestamp; only findings on or after this time.
        limit: Maximum findings to collect (default 500).
    """
    def _run() -> dict:
        tio = get_client()
        kwargs: dict[str, Any] = {}
        if severity:
            kwargs["severity"] = severity
        if since is not None:
            kwargs["since"] = since

        findings: list[dict] = []
        for item in tio.exports.vulns(**kwargs):
            findings.append(item)
            if len(findings) >= limit:
                break
        return {"count": len(findings), "findings": _jsonable(findings)}

    return _safe_call(_run)


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------

@mcp.tool()
def list_assets(limit: int = 100) -> dict:
    """List assets known to Tenable.io (via the workbenches endpoint).

    Args:
        limit: Maximum number of assets to return (default 100).
    """
    def _run() -> dict:
        tio = get_client()
        assets: list[dict] = []
        for item in tio.workbenches.assets():
            assets.append(item)
            if len(assets) >= limit:
                break
        return {"count": len(assets), "assets": _jsonable(assets)}

    return _safe_call(_run)


@mcp.tool()
def get_asset(asset_uuid: str) -> dict:
    """Get full details for a single asset by UUID."""
    def _run() -> dict:
        tio = get_client()
        return _jsonable(tio.workbenches.asset_info(asset_uuid))

    return _safe_call(_run)


@mcp.tool()
def search_assets(
    hostname: str | None = None,
    ipv4: str | None = None,
    tag_category: str | None = None,
    tag_value: str | None = None,
    limit: int = 100,
) -> dict:
    """Search assets with optional filters (hostname, IPv4, tag).

    Args:
        hostname: Substring match on hostname.
        ipv4: Exact-match IPv4 address.
        tag_category: Tag category name.
        tag_value: Tag value; requires tag_category.
        limit: Maximum number of assets to return (default 100).
    """
    def _run() -> dict:
        tio = get_client()
        filters: list[tuple[str, str, str]] = []
        if hostname:
            filters.append(("host.hostname", "match", hostname))
        if ipv4:
            filters.append(("host.ipv4", "eq", ipv4))
        if tag_category and tag_value:
            filters.append((f"tag.{tag_category}", "eq", tag_value))

        assets: list[dict] = []
        iterator = tio.workbenches.assets(*filters) if filters else tio.workbenches.assets()
        for item in iterator:
            assets.append(item)
            if len(assets) >= limit:
                break
        return {"count": len(assets), "assets": _jsonable(assets)}

    return _safe_call(_run)


# ---------------------------------------------------------------------------
# Plugins
# ---------------------------------------------------------------------------

@mcp.tool()
def get_plugin_info(plugin_id: int) -> dict:
    """Return full plugin metadata (description, solution, CVEs, CVSS) for a plugin ID.

    Args:
        plugin_id: Nessus plugin ID, e.g. 19506.
    """
    def _run() -> dict:
        tio = get_client()
        return _jsonable(tio.plugins.plugin_details(plugin_id))

    return _safe_call(_run)


@mcp.tool()
def list_plugin_families() -> dict:
    """List Nessus plugin families and their plugin counts."""
    def _run() -> dict:
        tio = get_client()
        families = list(tio.plugins.families())
        return {"count": len(families), "families": _jsonable(families)}

    return _safe_call(_run)


# ---------------------------------------------------------------------------
# Scanners, folders, networks
# ---------------------------------------------------------------------------

@mcp.tool()
def list_scanners() -> dict:
    """List scanners (cloud + on-prem) registered with Tenable.io."""
    def _run() -> dict:
        tio = get_client()
        scanners = list(tio.scanners.list())
        return {"count": len(scanners), "scanners": _jsonable(scanners)}

    return _safe_call(_run)


@mcp.tool()
def list_folders() -> dict:
    """List scan folders defined in Tenable.io."""
    def _run() -> dict:
        tio = get_client()
        folders = list(tio.folders.list())
        return {"count": len(folders), "folders": _jsonable(folders)}

    return _safe_call(_run)


@mcp.tool()
def list_networks() -> dict:
    """List network objects (logical network segments) in Tenable.io."""
    def _run() -> dict:
        tio = get_client()
        networks = list(tio.networks.list())
        return {"count": len(networks), "networks": _jsonable(networks)}

    return _safe_call(_run)


# ---------------------------------------------------------------------------
# Agents / agent groups
# ---------------------------------------------------------------------------

@mcp.tool()
def list_agents(limit: int = 200, scanner_id: int = 1) -> dict:
    """List Nessus agents connected to Tenable.io.

    Args:
        limit: Maximum number of agents to return (default 200).
        scanner_id: Parent scanner ID; the cloud scanner is 1 in Tenable.io.
    """
    def _run() -> dict:
        tio = get_client()
        agents: list[dict] = []
        for item in tio.agents.list(scanner_id=scanner_id):
            agents.append(item)
            if len(agents) >= limit:
                break
        return {"count": len(agents), "agents": _jsonable(agents)}

    return _safe_call(_run)


@mcp.tool()
def list_agent_groups(scanner_id: int = 1) -> dict:
    """List agent groups. Defaults to the cloud scanner (scanner_id=1)."""
    def _run() -> dict:
        tio = get_client()
        groups = list(tio.agent_groups.list(scanner_id=scanner_id))
        return {"count": len(groups), "groups": _jsonable(groups)}

    return _safe_call(_run)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

@mcp.tool()
def list_tag_categories() -> dict:
    """List all tag categories defined in Tenable.io."""
    def _run() -> dict:
        tio = get_client()
        cats = list(tio.tags.list_categories())
        return {"count": len(cats), "categories": _jsonable(cats)}

    return _safe_call(_run)


@mcp.tool()
def list_tag_values(category: str | None = None, limit: int = 200) -> dict:
    """List tag values, optionally filtered by category name.

    Args:
        category: Tag category name to filter by.
        limit: Maximum values to return (default 200).
    """
    def _run() -> dict:
        tio = get_client()
        filters = (("category_name", "eq", category),) if category else ()
        values: list[dict] = []
        iterator = tio.tags.list(*filters) if filters else tio.tags.list()
        for item in iterator:
            values.append(item)
            if len(values) >= limit:
                break
        return {"count": len(values), "values": _jsonable(values)}

    return _safe_call(_run)


# ---------------------------------------------------------------------------
# Exports - assets (pairs with export_vulnerabilities)
# ---------------------------------------------------------------------------

@mcp.tool()
def export_assets(
    chunk_size: int = 1000,
    since: int | None = None,
    limit: int = 1000,
) -> dict:
    """Stream assets from the asset export API.

    Args:
        chunk_size: Tenable export chunk size (default 1000).
        since: Unix timestamp; only assets updated on/after this time.
        limit: Maximum assets to collect in this call (default 1000).
    """
    def _run() -> dict:
        tio = get_client()
        kwargs: dict[str, Any] = {"chunk_size": chunk_size}
        if since is not None:
            kwargs["updated_at"] = since
        assets: list[dict] = []
        for item in tio.exports.assets(**kwargs):
            assets.append(item)
            if len(assets) >= limit:
                break
        return {"count": len(assets), "assets": _jsonable(assets)}

    return _safe_call(_run)


# ---------------------------------------------------------------------------
# Scan templates / policies
# ---------------------------------------------------------------------------

@mcp.tool()
def list_scan_templates() -> dict:
    """List scan templates available in Tenable.io (what types of scans can be built)."""
    def _run() -> dict:
        tio = get_client()
        templates = list(tio.policies.templates().values()) \
            if hasattr(tio.policies, "templates") else list(tio.editor.list("scan"))
        return {"count": len(templates), "templates": _jsonable(templates)}

    return _safe_call(_run)


@mcp.tool()
def list_policies() -> dict:
    """List user-defined scan policies."""
    def _run() -> dict:
        tio = get_client()
        policies = list(tio.policies.list())
        return {"count": len(policies), "policies": _jsonable(policies)}

    return _safe_call(_run)


# ---------------------------------------------------------------------------
# Server info / health
# ---------------------------------------------------------------------------

@mcp.tool()
def server_info() -> dict:
    """Return metadata about the connected Tenable.io tenant (sanity / health check)."""
    def _run() -> dict:
        tio = get_client()
        info: dict[str, Any] = {}
        try:
            info["session"] = tio.session.details()
        except Exception as exc:  # noqa: BLE001
            info["session_error"] = str(exc)
        try:
            info["server"] = tio.server.properties()
        except Exception as exc:  # noqa: BLE001
            info["server_error"] = str(exc)
        return _jsonable(info)

    return _safe_call(_run)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """Console entrypoint. Selects transport based on TRANSPORT env var."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    transport = os.environ.get("TRANSPORT", "stdio").lower()
    if transport == "stdio":
        logger.info("Starting pytenable-mcp on stdio transport")
        mcp.run(transport="stdio")
    elif transport in ("http", "sse"):
        host = os.environ.get("HTTP_HOST", "0.0.0.0")
        port = int(os.environ.get("HTTP_PORT", "8000"))
        # FastMCP reads host/port from its own settings object.
        mcp.settings.host = host
        mcp.settings.port = port
        logger.info("Starting pytenable-mcp on SSE transport at %s:%d", host, port)
        mcp.run(transport="sse")
    else:
        raise SystemExit(
            f"Unknown TRANSPORT={transport!r}. Use 'stdio' or 'http'."
        )


if __name__ == "__main__":
    main()
