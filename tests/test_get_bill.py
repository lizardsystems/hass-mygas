"""Tests for get_bill default date resolution."""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mygas.const import DOMAIN, SERVICE_GET_BILL
from custom_components.mygas.helpers import make_account_device_id

from .const import MOCK_LSPU_INFO_NO_BALANCES, MOCK_LSPU_INFO_RESPONSE


def _get_account_device(hass: HomeAssistant) -> dr.DeviceEntry:
    """Return the account-level device entry."""
    device_registry = dr.async_get(hass)
    account_number = MOCK_LSPU_INFO_RESPONSE["account"]
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_account_device_id(account_number))}
    )
    assert device is not None
    return device


# ---------------------------------------------------------------------------
# get_bill without date uses balances[0]["date"]
# ---------------------------------------------------------------------------


async def test_get_bill_no_date_uses_balances(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """When no date is given, get_bill should use balances[0]['date']."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    device = _get_account_device(hass)

    result = await coordinator.async_get_bill(device.id)
    assert result is not None

    # The API should have been called with the date from balances
    expected_date = MOCK_LSPU_INFO_RESPONSE["balances"][0]["date"]  # "2026-01-31"
    mock_api.async_get_receipt.assert_called_once()
    call_args = mock_api.async_get_receipt.call_args
    assert call_args[0][0] == expected_date


# ---------------------------------------------------------------------------
# get_bill without date and empty balances falls back to 1st of prev month
# ---------------------------------------------------------------------------


async def test_get_bill_no_date_empty_balances_fallback(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """When balances is empty, get_bill should fall back to 1st of previous month."""
    mock_api.async_get_lspu_info = AsyncMock(return_value=MOCK_LSPU_INFO_NO_BALANCES)
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    device = _get_account_device(hass)

    result = await coordinator.async_get_bill(device.id)
    assert result is not None

    # Fallback: 1st of previous month
    today = dt_util.now().date()
    first_of_prev = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    expected_date = first_of_prev.strftime("%Y-%m-%d")
    mock_api.async_get_receipt.assert_called_once()
    call_args = mock_api.async_get_receipt.call_args
    assert call_args[0][0] == expected_date


# ---------------------------------------------------------------------------
# get_bill with explicit date still works
# ---------------------------------------------------------------------------


async def test_get_bill_with_explicit_date(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """When a date is explicitly provided, get_bill should use it directly."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    device = _get_account_device(hass)

    explicit_date = date(2025, 6, 15)
    result = await coordinator.async_get_bill(device.id, bill_date=explicit_date)
    assert result is not None

    mock_api.async_get_receipt.assert_called_once()
    call_args = mock_api.async_get_receipt.call_args
    assert call_args[0][0] == "2025-06-15"


# ---------------------------------------------------------------------------
# Service call with email passes schema validation (regression for issue #21)
# ---------------------------------------------------------------------------


async def test_get_bill_service_with_email(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Service call with email must validate to a string, not a function.

    Regression for issue #21: vol.Email (without parens) is a factory; using
    it directly turned the validated email into a function reference, which
    later failed JSON serialization with "Type is not JSON serializable: function".
    """
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device = _get_account_device(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_BILL,
        {
            "device_id": device.id,
            "date": "2026-04-27",
            "email": "user@example.com",
        },
        blocking=True,
    )

    mock_api.async_get_receipt.assert_called_once()
    call_args = mock_api.async_get_receipt.call_args
    assert call_args[0][1] == "user@example.com"
