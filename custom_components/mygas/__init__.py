"""MyGas Account integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import MyGasCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up MyGas from a config entry."""

    # Set up the Coordinator
    _coordinator = MyGasCoordinator(hass, _LOGGER, config_entry=config_entry)

    # Sync with Coordinator
    await _coordinator.async_config_entry_first_refresh()

    # Store Entity and Initialize Platforms
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = _coordinator

    # Listen for option changes
    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
            config_entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(config_entry.entry_id)

        await async_unload_services(hass)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)
