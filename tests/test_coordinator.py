"""Tests for the MyGas coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from aiomygas.exceptions import MyGasApiError, MyGasAuthError, MyGasConnectionError
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mygas.const import API_MAX_TRIES, CONF_INFO


# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------


async def test_coordinator_first_refresh(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test coordinator first refresh loads data."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    coordinator = mock_config_entry.runtime_data
    assert coordinator.data is not None
    assert CONF_INFO in coordinator.data


async def test_coordinator_accounts_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test coordinator retrieves accounts data correctly."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    accounts = coordinator.get_accounts()
    assert len(accounts) > 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


async def test_coordinator_auth_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test coordinator handles auth errors."""
    mock_api.async_get_accounts.side_effect = MyGasAuthError("Auth failed")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_coordinator_api_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test coordinator handles API errors with retry."""
    mock_api.async_get_accounts.side_effect = MyGasApiError("API error")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


# ---------------------------------------------------------------------------
# Network failures during sign-in (issue #23)
# ---------------------------------------------------------------------------


def _failing_session() -> MagicMock:
    """Return a client session whose requests fail with a DNS error."""
    session = MagicMock()
    session.post.side_effect = aiohttp.ClientConnectionError(
        "Cannot connect to host: DNS server returned general failure"
    )
    return session


async def test_setup_dns_failure_retries_instead_of_reauth(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A DNS failure while getting a token must not ask for the password."""
    mock_config_entry.add_to_hass(hass)
    session = _failing_session()

    with patch(
        "custom_components.mygas.coordinator.async_get_clientsession",
        return_value=session,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
    # The sign-in was retried, which only happens for transient errors
    assert session.post.call_count == API_MAX_TRIES
    assert not list(
        mock_config_entry.async_get_active_flows(hass, {SOURCE_REAUTH})
    )


async def test_setup_connection_error_retries(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """MyGasConnectionError on first refresh leads to setup retry."""
    mock_api.async_get_accounts.side_effect = MyGasConnectionError("timeout")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
    assert not list(
        mock_config_entry.async_get_active_flows(hass, {SOURCE_REAUTH})
    )


async def test_successful_update_aborts_stale_reauth(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """A successful update closes a reauth flow that is no longer needed."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await mock_config_entry.start_reauth_flow(hass)
    assert list(mock_config_entry.async_get_active_flows(hass, {SOURCE_REAUTH}))

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success
    assert not list(
        mock_config_entry.async_get_active_flows(hass, {SOURCE_REAUTH})
    )
