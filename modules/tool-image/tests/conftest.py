"""Tests use synthetic credentials and injected transports, never real services."""

import socket

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("A test attempted a real network connection")

    monkeypatch.setattr(socket.socket, "connect", refused)
    monkeypatch.setattr(socket.socket, "connect_ex", refused)
    monkeypatch.setattr(socket, "getaddrinfo", refused)
