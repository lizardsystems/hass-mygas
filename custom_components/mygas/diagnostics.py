"""Diagnostics support for MyGas."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import MyGasConfigEntry

TO_REDACT_CONFIG = {"username", "password"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MyGasConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    return {
        "config_entry": async_redact_data(dict(entry.data), TO_REDACT_CONFIG),
        "coordinator_data": async_redact_data(
            coordinator.data or {}, TO_REDACT_CONFIG
        ),
    }
