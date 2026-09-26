"""Offline composition must not create clients, resolve accounts, or call services."""
import socket

import pytest


@pytest.fixture(autouse=True)
def isolated_home_and_no_network(tmp_path, monkeypatch):
    monkeypatch.setenv("AMPLIFIER_HOME", str(tmp_path / "amplifier"))
    for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    def refused(*args, **kwargs):
        raise AssertionError("Offline composition attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", refused)
    monkeypatch.setattr(socket.socket, "connect_ex", refused)
    monkeypatch.setattr(socket, "getaddrinfo", refused)
