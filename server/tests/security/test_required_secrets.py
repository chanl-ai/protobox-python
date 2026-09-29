"""The server must refuse to start with a missing, short, or publicly known signing or
encryption key. With the old built-in defaults, anyone who read the source could forge
login tokens and decrypt stored secrets."""

import pytest

from protobox.admin.config import Settings

STRONG = "x" * 40
KNOWN_DEFAULTS = ["development-jwt-secret", "development-secret-key-12345"]


def settings_with(monkeypatch, **env):
    for key in ("JWT_SECRET", "MCP_SECRET_KEY"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings()


@pytest.mark.parametrize("missing", ["JWT_SECRET", "MCP_SECRET_KEY"])
def test_missing_key_is_refused(monkeypatch, missing):
    env = {"JWT_SECRET": STRONG, "MCP_SECRET_KEY": STRONG}
    env.pop(missing)
    s = settings_with(monkeypatch, **env)
    with pytest.raises(ValueError, match=missing):
        s.validate_required_secrets()


@pytest.mark.parametrize("key", ["JWT_SECRET", "MCP_SECRET_KEY"])
@pytest.mark.parametrize("weak", KNOWN_DEFAULTS + ["short-key"])
def test_known_or_short_key_is_refused(monkeypatch, key, weak):
    env = {"JWT_SECRET": STRONG, "MCP_SECRET_KEY": STRONG, key: weak}
    s = settings_with(monkeypatch, **env)
    with pytest.raises(ValueError, match=key):
        s.validate_required_secrets()


def test_strong_keys_are_accepted(monkeypatch):
    s = settings_with(monkeypatch, JWT_SECRET=STRONG, MCP_SECRET_KEY="y" * 40)
    s.validate_required_secrets()


def test_no_builtin_default_is_used(monkeypatch):
    s = settings_with(monkeypatch)
    assert not s.jwt_secret
    assert not s._secret_encryption_key
