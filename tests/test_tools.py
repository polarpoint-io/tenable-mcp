"""Tool-level tests that mock the Tenable.io client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pytenable_mcp import server


def _mock_tio(**attrs):
    mock = MagicMock()
    for name, value in attrs.items():
        setattr(mock, name, value)
    return mock


@patch("pytenable_mcp.server.get_client")
def test_list_scans(get_client):
    scans_api = MagicMock()
    scans_api.list.return_value = iter([{"id": 1, "name": "Daily"}])
    get_client.return_value = _mock_tio(scans=scans_api)

    result = server.list_scans()
    assert result["count"] == 1
    assert result["scans"][0]["id"] == 1


@patch("pytenable_mcp.server.get_client")
def test_launch_scan(get_client):
    scans_api = MagicMock()
    scans_api.launch.return_value = "abc-123"
    get_client.return_value = _mock_tio(scans=scans_api)

    result = server.launch_scan(scan_id=42, targets=["10.0.0.1"])
    assert result == {"scan_id": 42, "scan_uuid": "abc-123"}
    scans_api.launch.assert_called_once_with(42, targets=["10.0.0.1"])


@patch("pytenable_mcp.server.get_client")
def test_get_plugin_info(get_client):
    plugins_api = MagicMock()
    plugins_api.plugin_details.return_value = {"id": 19506, "name": "Nessus Scan Info"}
    get_client.return_value = _mock_tio(plugins=plugins_api)

    result = server.get_plugin_info(plugin_id=19506)
    assert result["id"] == 19506


@patch("pytenable_mcp.server.get_client")
def test_error_surfaces_cleanly(get_client):
    scans_api = MagicMock()
    scans_api.list.side_effect = RuntimeError("boom")
    get_client.return_value = _mock_tio(scans=scans_api)

    result = server.list_scans()
    assert result["error"] == "RuntimeError"
    assert "boom" in result["message"]
