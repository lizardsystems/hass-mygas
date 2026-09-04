"""MyGas Account integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import ATTR_UUID, DOMAIN, PLATFORMS
from .coordinator import MyGasCoordinator
from .entity import account_device_info
from .helpers import make_account_device_id, make_device_id, make_service_device_id
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

type MyGasConfigEntry = ConfigEntry[MyGasCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MyGasConfigEntry) -> bool:
    """Set up MyGas from a config entry."""
    coordinator = MyGasCoordinator(hass, config_entry=entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    _async_remove_stale_devices(hass, entry, coordinator)
    _async_register_account_devices(hass, entry, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await async_setup_services(hass)

    return True


def _async_register_account_devices(
    hass: HomeAssistant,
    entry: MyGasConfigEntry,
    coordinator: MyGasCoordinator,
) -> None:
    """Register the account devices.

    Counter and service devices link to their account with `via_device_id`, which
    needs the account device to exist before the platforms add their entities.
    """
    device_registry = dr.async_get(hass)

    for account_id, lspu_account_id in coordinator.iter_lspu_accounts():
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            **account_device_info(coordinator, account_id, lspu_account_id),
        )


def _async_remove_stale_devices(
    hass: HomeAssistant,
    entry: MyGasConfigEntry,
    coordinator: MyGasCoordinator,
) -> None:
    """Remove device entries for counters that no longer exist."""
    device_registry = dr.async_get(hass)

    current_identifiers: set[str] = set()
    for account_id, lspu_account_id in coordinator.iter_lspu_accounts():
        account_number = coordinator.get_account_number(account_id, lspu_account_id)
        # Account-level device (always present)
        current_identifiers.add(make_account_device_id(account_number))
        # Counter-level devices
        for counter in coordinator.get_counters(account_id, lspu_account_id):
            counter_uuid = counter.get(ATTR_UUID)
            if counter_uuid:
                current_identifiers.add(make_device_id(account_number, counter_uuid))
        # Service-level devices
        for service in coordinator.get_services(account_id, lspu_account_id):
            service_id = service.get("id")
            if service_id:
                current_identifiers.add(
                    make_service_device_id(account_number, service_id)
                )

    for device_entry in dr.async_entries_for_config_entry(
        device_registry, entry.entry_id
    ):
        if not any(
            ident[0] == DOMAIN and ident[1] in current_identifiers
            for ident in device_entry.identifiers
        ):
            _LOGGER.info(
                "Removing stale device %s (%s)",
                device_entry.name,
                device_entry.id,
            )
            device_registry.async_remove_device(device_entry.id)


async def async_unload_entry(hass: HomeAssistant, entry: MyGasConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
