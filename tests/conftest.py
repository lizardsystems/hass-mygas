"""Fixtures for MyGas integration tests."""
from __future__ import annotations

import socket
import sys

if sys.platform == "win32":
    # On Windows, all event loops need socket.socketpair() for self-pipe,
    # but pytest-socket replaces socket.socket with GuardedSocket that blocks
    # creation. Save the real socket class now (before pytest-socket activates)
    # and patch socketpair to bypass the guard.
    _real_socket_cls = socket.socket
    _real_socketpair = socket.socketpair

    def _safe_socketpair(*args, **kwargs):  # type: ignore[no-untyped-def]
        saved = socket.socket
        socket.socket = _real_socket_cls
        try:
            return _real_socketpair(*args, **kwargs)
        finally:
            socket.socket = saved

    socket.socketpair = _safe_socketpair  # type: ignore[assignment]

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mygas.const import DOMAIN

from .const import (
    MOCK_ACCOUNTS_RESPONSE,
    MOCK_LSPU_INFO_RESPONSE,
    MOCK_PASSWORD,
    MOCK_RECEIPT_RESPONSE,
    MOCK_SEND_READINGS_RESPONSE,
    MOCK_USERNAME,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable custom integrations for all tests."""


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Eliminate retry delays in tests."""
    monkeypatch.setattr(
        "custom_components.mygas.decorators.API_RETRY_DELAY", 0
    )


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_PASSWORD: MOCK_PASSWORD,
        },
        unique_id=MOCK_USERNAME,
        version=1,
    )


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Mock async_setup_entry."""
    with patch(
        "custom_components.mygas.async_setup_entry", return_value=True
    ) as mock:
        yield mock


@pytest.fixture
def mock_validate() -> Generator[AsyncMock]:
    """Mock _async_validate_credentials."""
    with patch(
        "custom_components.mygas.config_flow._async_validate_credentials",
        return_value={"title": MOCK_USERNAME},
    ) as mock:
        yield mock


@pytest.fixture
def mock_api() -> Generator[AsyncMock]:
    """Mock MyGasApi for coordinator tests."""
    with patch(
        "custom_components.mygas.coordinator.MyGasApi"
    ) as mock_api_cls:
        mock_instance = mock_api_cls.return_value
        mock_instance.async_get_accounts = AsyncMock(
            return_value=MOCK_ACCOUNTS_RESPONSE
        )
        mock_instance.async_get_lspu_info = AsyncMock(
            return_value=MOCK_LSPU_INFO_RESPONSE
        )
        mock_instance.async_indication_send = AsyncMock(
            return_value=MOCK_SEND_READINGS_RESPONSE
        )
        mock_instance.async_get_receipt = AsyncMock(
            return_value=MOCK_RECEIPT_RESPONSE
        )
        mock_instance.async_get_client_info = AsyncMock(return_value={})
        mock_instance.async_get_els_info = AsyncMock(return_value={})
        mock_instance.async_get_charges = AsyncMock(return_value={})
        mock_instance.async_get_payments = AsyncMock(return_value={})
        yield mock_instance


@pytest.fixture
def mock_auth() -> Generator[AsyncMock]:
    """Mock SimpleMyGasAuth for coordinator tests."""
    with patch(
        "custom_components.mygas.coordinator.SimpleMyGasAuth"
    ) as mock_auth_cls:
        mock_instance = mock_auth_cls.return_value
        yield mock_instance
