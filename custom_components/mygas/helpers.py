"""MyGas helper function."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util, slugify

from .const import ATTR_COUNTER, DOMAIN

if TYPE_CHECKING:
    from .coordinator import MyGasCoordinator


async def async_get_device_entry_by_device_id(
    hass: HomeAssistant, device_id: str | None
) -> dr.DeviceEntry:
    """Get device entry by device id."""
    if device_id is None:
        raise ValueError("Device is undefined")

    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get(device_id)
    if device_entry:
        return device_entry

    raise ValueError(f"Device {device_id} not found")


async def async_get_coordinator(
    hass: HomeAssistant, device_id: str | None
) -> MyGasCoordinator:
    """Get coordinator for device id."""
    device_entry = await async_get_device_entry_by_device_id(hass, device_id)
    for entry_id in device_entry.config_entries:
        if (config_entry := hass.config_entries.async_get_entry(entry_id)) is None:
            continue
        if config_entry.domain == DOMAIN:
            return config_entry.runtime_data

    raise ValueError(f"Config entry for {device_id} not found")


def get_float_value(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Get float value from entity state."""
    if entity_id is not None:
        cur_state = hass.states.get(entity_id)
        if cur_state is not None:
            return _to_float(cur_state.state)
    return None


def get_update_interval(hour: int, minute: int, second: int) -> timedelta:
    """Get update interval to time."""
    now = dt_util.now()
    next_day = now + timedelta(days=1)
    next_time = next_day.replace(hour=hour, minute=minute, second=second)
    minutes_to_next_time = (next_time - now).total_seconds() / 60
    return timedelta(minutes=minutes_to_next_time)


def get_bill_date() -> date:
    """Get first day of current month."""
    today = date.today()
    return today.replace(day=1)  # first day of current month


def _to_str(value: Any) -> str | None:
    """Convert value to string."""
    if value is None:
        return None
    try:
        s = str(value)
    except (TypeError, ValueError):
        return None

    return s


def _to_float(value: Any) -> float | None:
    """Convert value to float."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None

    return f


def _to_int(value: Any) -> int | None:
    """Convert value to int."""
    if value is None:
        return None
    try:
        i = int(value)
    except (TypeError, ValueError):
        return None

    return i


def _to_date(value: str | None, fmt: str) -> date | None:
    """Convert string value to date."""
    if not value:
        return None
    try:
        d = datetime.strptime(value, fmt).date()
    except (TypeError, ValueError):
        return None

    return d


def make_entity_unique_id(device_identifier: str, key: str) -> str:
    """Build unique_id from device identifier and entity key."""
    return slugify(f"{DOMAIN}_{device_identifier}_{key}")


def make_account_device_id(account_number: str) -> str:
    """Get account-level device id."""
    return slugify(f"{account_number}_account")


def make_device_id(account_number: str, counter_uuid: str) -> str:
    """Get device id."""
    return slugify(f"{account_number}_{ATTR_COUNTER}_{counter_uuid}")
