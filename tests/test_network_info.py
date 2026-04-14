"""Tests for the /api/network-info endpoint (LAN IP hint)."""

import importlib
import json
import types
from unittest.mock import AsyncMock, MagicMock, patch


def _make_request():
    """Create a minimal fake Starlette Request."""
    scope = {"type": "http", "method": "GET", "path": "/api/network-info"}
    return MagicMock(scope=scope)


def _import_server():
    """Import server module (lazy, avoids side-effects from module-level code)."""
    import server
    return server


def test_api_network_info_exists():
    """api_network_info function is defined in server.py."""
    srv = _import_server()
    assert hasattr(srv, "api_network_info"), "api_network_info not found in server module"
    assert callable(srv.api_network_info)


def test_api_network_info_returns_json_response():
    """api_network_info returns a JSONResponse with ips and port keys."""
    import asyncio
    srv = _import_server()
    req = _make_request()

    # Mock socket to return a known IP
    mock_socket = MagicMock()
    mock_socket.getsockname.return_value = ("192.168.1.42", 12345)

    with patch("socket.socket", return_value=mock_socket):
        resp = asyncio.run(srv.api_network_info(req))

    body = json.loads(resp.body.decode())
    assert "ips" in body
    assert "port" in body
    assert isinstance(body["ips"], list)
    assert "192.168.1.42" in body["ips"]


def test_api_network_info_fallback_on_socket_error():
    """When primary socket probe fails, falls back to getaddrinfo."""
    import asyncio
    srv = _import_server()
    req = _make_request()

    def socket_that_fails(*a, **kw):
        s = MagicMock()
        s.connect.side_effect = OSError("no route")
        return s

    fake_addrinfo = [
        (2, 1, 6, "", ("10.0.0.5", 0)),
        (2, 1, 6, "", ("127.0.0.1", 0)),  # should be filtered
    ]

    with patch("socket.socket", side_effect=socket_that_fails), \
         patch("socket.gethostname", return_value="myhost"), \
         patch("socket.getaddrinfo", return_value=fake_addrinfo):
        resp = asyncio.run(srv.api_network_info(req))

    body = json.loads(resp.body.decode())
    assert "10.0.0.5" in body["ips"]
    assert "127.0.0.1" not in body["ips"]


def test_api_network_info_empty_when_all_fail():
    """Returns empty ips list when all detection methods fail."""
    import asyncio
    srv = _import_server()
    req = _make_request()

    def socket_that_fails(*a, **kw):
        s = MagicMock()
        s.connect.side_effect = OSError("no route")
        return s

    with patch("socket.socket", side_effect=socket_that_fails), \
         patch("socket.gethostname", side_effect=OSError("no hostname")):
        resp = asyncio.run(srv.api_network_info(req))

    body = json.loads(resp.body.decode())
    assert body["ips"] == []
    assert "port" in body


def test_api_network_info_uses_env_port():
    """Port is read from OUROBOROS_SERVER_PORT env var."""
    import asyncio
    srv = _import_server()
    req = _make_request()

    mock_socket = MagicMock()
    mock_socket.getsockname.return_value = ("192.168.0.1", 0)

    with patch("socket.socket", return_value=mock_socket), \
         patch.dict("os.environ", {"OUROBOROS_SERVER_PORT": "9999"}):
        resp = asyncio.run(srv.api_network_info(req))

    body = json.loads(resp.body.decode())
    assert body["port"] == 9999


def test_route_registered():
    """The /api/network-info route is present in the routes list."""
    srv = _import_server()
    paths = []
    for r in srv.routes:
        if hasattr(r, "path"):
            paths.append(r.path)
    assert "/api/network-info" in paths, f"/api/network-info not in registered routes: {paths}"


def test_settings_js_has_update_lan_hint():
    """settings.js contains the updateLanHint function and wiring."""
    from pathlib import Path
    js = Path("web/modules/settings.js").read_text()
    assert "updateLanHint" in js, "updateLanHint function not found in settings.js"
    assert "lan-access-hint" in js or "lan-access-hint" in Path("web/modules/settings_ui.js").read_text(), \
        "lan-access-hint element not found in settings JS/UI"
    assert "api/network-info" in js, "/api/network-info fetch not found in settings.js"


def test_settings_ui_has_hint_div():
    """settings_ui.js contains the lan-access-hint div."""
    from pathlib import Path
    ui = Path("web/modules/settings_ui.js").read_text()
    assert "lan-access-hint" in ui, "lan-access-hint div not found in settings_ui.js"


def test_css_has_lan_hint_link():
    """settings.css contains .lan-hint-link styling."""
    from pathlib import Path
    css = Path("web/settings.css").read_text()
    assert ".lan-hint-link" in css, ".lan-hint-link class not found in settings.css"
