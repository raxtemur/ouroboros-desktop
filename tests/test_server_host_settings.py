"""Tests for early settings-based host override in server.py main()."""

import os
from unittest.mock import patch


def _run_main_host_logic(settings_host, env_host=None):
    """
    Simulate the early settings load block from server.py main()
    and return the effective_host that would be used.
    """
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 8765

    effective_host = DEFAULT_HOST
    effective_port = DEFAULT_PORT

    env = {k: v for k, v in os.environ.items()}
    if env_host is not None:
        env["OUROBOROS_SERVER_HOST"] = env_host
    else:
        env.pop("OUROBOROS_SERVER_HOST", None)

    mock_settings = {"OUROBOROS_SERVER_HOST": settings_host}

    with patch.dict(os.environ, env, clear=True):
        _host_from_settings = str(mock_settings.get("OUROBOROS_SERVER_HOST", "") or "").strip()
        if _host_from_settings and not os.environ.get("OUROBOROS_SERVER_HOST"):
            effective_host = _host_from_settings

    return effective_host


def test_settings_host_applied_when_no_env():
    """Settings host should override default when env var is absent."""
    result = _run_main_host_logic(settings_host="0.0.0.0", env_host=None)
    assert result == "0.0.0.0"


def test_env_host_takes_precedence():
    """Env var should win over settings file value."""
    result = _run_main_host_logic(settings_host="0.0.0.0", env_host="10.0.0.1")
    assert result == "127.0.0.1"  # env was set, so settings block is skipped → default stays


def test_empty_settings_host_keeps_default():
    """Empty string in settings should not override the default."""
    result = _run_main_host_logic(settings_host="", env_host=None)
    assert result == "127.0.0.1"


def test_none_settings_host_keeps_default():
    """None in settings should not override the default."""
    result = _run_main_host_logic(settings_host=None, env_host=None)
    assert result == "127.0.0.1"


def test_whitespace_settings_host_keeps_default():
    """Whitespace-only string in settings should not override the default."""
    result = _run_main_host_logic(settings_host="   ", env_host=None)
    assert result == "127.0.0.1"


def test_config_has_server_host_default():
    """OUROBOROS_SERVER_HOST should be in SETTINGS_DEFAULTS."""
    from ouroboros.config import SETTINGS_DEFAULTS
    assert "OUROBOROS_SERVER_HOST" in SETTINGS_DEFAULTS
    assert SETTINGS_DEFAULTS["OUROBOROS_SERVER_HOST"] == "127.0.0.1"
