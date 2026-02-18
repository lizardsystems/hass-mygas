"""Tests for the MyGas integration setup."""
from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


# ---------------------------------------------------------------------------
# Setup / unload
# ---------------------------------------------------------------------------


async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test successful setup of a config entry."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data is not None


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test successful unload of a config entry."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_entry_auth_failed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test setup when authentication fails."""
    from aiomygas.exceptions import MyGasAuthError

    mock_api.async_get_accounts.side_effect = MyGasAuthError("Invalid credentials")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_entry_api_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test setup when API call fails."""
    from aiomygas.exceptions import MyGasApiError

    mock_api.async_get_accounts.side_effect = MyGasApiError("API error")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


# ---------------------------------------------------------------------------
# Stale device removal
# ---------------------------------------------------------------------------


async def test_stale_device_removal(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that stale devices are removed after setup."""
    from homeassistant.helpers import device_registry as dr

    from custom_components.mygas.const import DOMAIN

    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)

    # Create a stale device (counter that no longer exists)
    device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "old_account_counter_old_uuid")},
    )

    stale_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "old_account_counter_old_uuid")}
    )
    assert stale_device is not None

    # Reload — stale device cleanup happens on setup
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Stale device should be removed
    stale_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "old_account_counter_old_uuid")}
    )
    assert stale_device is None

    # Valid device should still exist (make_device_id("1234567890", "abc-def-123"))
    valid_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "1234567890_counter_abc_def_123")}
    )
    assert valid_device is not None
