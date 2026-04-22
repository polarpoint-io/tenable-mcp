"""pytenable-mcp: MCP server exposing Tenable.io via pyTenable."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pytenable-mcp")
except PackageNotFoundError:  # pragma: no cover - only when running from source uninstalled
    __version__ = "0.0.0"
