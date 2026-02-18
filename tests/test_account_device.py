"""Tests for account-level device hierarchy."""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mygas.const import DOMAIN
from custom_components.mygas.helpers import make_account_device_id, make_device_id

from .const import MOCK_LSPU_INFO_RESPONSE


# Response with no counters
MOCK_LSPU_INFO_NO_COUNTERS = {
    "account": "9876543210",
    "alias": "Дача",
    "accountId": 12345,
    "balance": 200.00,
    "parameters": [
        {"name": "Адрес", "value": "г. Москва, ул. Другая, д. 5"},
    ],
    "counters": [],
}

# Response without balances array
MOCK_LSPU_INFO_NO_BALANCES = {
    **MOCK_LSPU_INFO_RESPONSE,
    "balances": [],
}


# ---------------------------------------------------------------------------
# Account device creation (with counters)
# ---------------------------------------------------------------------------


async def test_account_device_created(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that an account-level device is created alongside counter devices."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    device_registry = dr.async_get(hass)

    # Account device should exist
    account_number = MOCK_LSPU_INFO_RESPONSE["account"]
    account_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_account_device_id(account_number))}
    )
    assert account_device is not None
    assert account_device.name == f"ЛС {MOCK_LSPU_INFO_RESPONSE['account']} ({MOCK_LSPU_INFO_RESPONSE['alias']})"

    # Counter device should also exist
    counter_uuid = MOCK_LSPU_INFO_RESPONSE["counters"][0]["uuid"]
    counter_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_device_id(account_number, counter_uuid))}
    )
    assert counter_device is not None


async def test_counter_device_via_device(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that counter devices link to the account device via via_device."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)

    account_number = MOCK_LSPU_INFO_RESPONSE["account"]
    account_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_account_device_id(account_number))}
    )
    assert account_device is not None

    counter_uuid = MOCK_LSPU_INFO_RESPONSE["counters"][0]["uuid"]
    counter_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_device_id(account_number, counter_uuid))}
    )
    assert counter_device is not None
    assert counter_device.via_device_id == account_device.id


# ---------------------------------------------------------------------------
# Account without counters
# ---------------------------------------------------------------------------


async def test_account_without_counters(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that account without counters still creates an account device with sensors."""
    mock_api.async_get_lspu_info = AsyncMock(return_value=MOCK_LSPU_INFO_NO_COUNTERS)
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    device_registry = dr.async_get(hass)

    # Account device should exist
    account_number = MOCK_LSPU_INFO_NO_COUNTERS["account"]
    account_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_account_device_id(account_number))}
    )
    assert account_device is not None
    assert account_device.name == f"ЛС {MOCK_LSPU_INFO_NO_COUNTERS['account']} ({MOCK_LSPU_INFO_NO_COUNTERS['alias']})"

    # No counter devices should exist
    devices = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )
    assert len(devices) == 1  # only account device


async def test_account_without_counters_has_sensors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that account without counters has balance and account sensors."""
    mock_api.async_get_lspu_info = AsyncMock(return_value=MOCK_LSPU_INFO_NO_COUNTERS)
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Look up entities by unique_id via entity registry
    ent_reg = er.async_get(hass)
    account_device_id = make_account_device_id(MOCK_LSPU_INFO_NO_COUNTERS["account"])

    balance_entry = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{account_device_id}_balance"
    )
    assert balance_entry is not None

    account_entry = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{account_device_id}_account"
    )
    assert account_entry is not None


async def test_account_without_counters_has_buttons(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that account without counters has refresh and get_bill buttons."""
    mock_api.async_get_lspu_info = AsyncMock(return_value=MOCK_LSPU_INFO_NO_COUNTERS)
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    account_device_id = make_account_device_id(MOCK_LSPU_INFO_NO_COUNTERS["account"])

    refresh_entry = ent_reg.async_get_entity_id(
        "button", DOMAIN, f"{DOMAIN}_{account_device_id}_refresh"
    )
    assert refresh_entry is not None

    get_bill_entry = ent_reg.async_get_entity_id(
        "button", DOMAIN, f"{DOMAIN}_{account_device_id}_get_bill"
    )
    assert get_bill_entry is not None


# ---------------------------------------------------------------------------
# Account sensors (with counters — sensors on both levels)
# ---------------------------------------------------------------------------


async def test_account_sensors_with_counters(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that account-level sensors exist when counters are present."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    account_device_id = make_account_device_id(MOCK_LSPU_INFO_RESPONSE["account"])

    balance_entity_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{account_device_id}_balance"
    )
    assert balance_entity_id is not None

    balance_state = hass.states.get(balance_entity_id)
    assert balance_state is not None


# ---------------------------------------------------------------------------
# find_account_by_device_id for account-level device
# ---------------------------------------------------------------------------


async def test_find_account_by_account_device(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that find_account_by_device_id works for account-level devices."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    device_registry = dr.async_get(hass)

    account_number = MOCK_LSPU_INFO_RESPONSE["account"]
    account_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_account_device_id(account_number))}
    )
    assert account_device is not None

    account_id, lspu_account_id, counter_id = (
        await coordinator.find_account_by_device_id(account_device.id)
    )
    assert account_id is not None
    assert lspu_account_id is not None
    assert counter_id is None  # account-level — no counter


# ---------------------------------------------------------------------------
# get_bill from account device
# ---------------------------------------------------------------------------


async def test_get_bill_from_account_device(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test get_bill works when called from an account-level device."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    device_registry = dr.async_get(hass)

    account_number = MOCK_LSPU_INFO_RESPONSE["account"]
    account_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_account_device_id(account_number))}
    )
    assert account_device is not None

    result = await coordinator.async_get_bill(account_device.id)
    assert result is not None
    assert "url" in result


# ---------------------------------------------------------------------------
# send_readings raises error for account-level device (no counter)
# ---------------------------------------------------------------------------


async def test_send_readings_fails_for_account_device(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that send_readings raises error for account-level device (no counter_id)."""
    from homeassistant.exceptions import HomeAssistantError
    import pytest

    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    device_registry = dr.async_get(hass)

    account_number = MOCK_LSPU_INFO_RESPONSE["account"]
    account_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_account_device_id(account_number))}
    )
    assert account_device is not None

    with pytest.raises(HomeAssistantError):
        await coordinator.async_send_readings(account_device.id, 100.0)


# ---------------------------------------------------------------------------
# Stale device removal includes account devices
# ---------------------------------------------------------------------------


async def test_stale_device_removal_keeps_account_device(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that stale removal keeps account device and removes old ones."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)

    # Create a stale device
    device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "old_stale_device_id")},
    )

    stale_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "old_stale_device_id")}
    )
    assert stale_device is not None

    # Reload — stale device cleanup happens on setup
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Stale device should be removed
    stale_device = device_registry.async_get_device(
        identifiers={(DOMAIN, "old_stale_device_id")}
    )
    assert stale_device is None

    # Account device should still exist
    account_number = MOCK_LSPU_INFO_RESPONSE["account"]
    account_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_account_device_id(account_number))}
    )
    assert account_device is not None

    # Counter device should still exist
    counter_uuid = MOCK_LSPU_INFO_RESPONSE["counters"][0]["uuid"]
    counter_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_device_id(account_number, counter_uuid))}
    )
    assert counter_device is not None


# ---------------------------------------------------------------------------
# Balance sensors — enabled by default
# ---------------------------------------------------------------------------


async def test_account_sensor_charged(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test charged sensor value."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    account_device_id = make_account_device_id(MOCK_LSPU_INFO_RESPONSE["account"])

    entity_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{account_device_id}_charged"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == 850.0


async def test_account_sensor_paid(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test paid sensor value."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    account_device_id = make_account_device_id(MOCK_LSPU_INFO_RESPONSE["account"])

    entity_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{account_device_id}_paid"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == 750.0


async def test_account_sensor_debt(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test debt sensor value."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    account_device_id = make_account_device_id(MOCK_LSPU_INFO_RESPONSE["account"])

    entity_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{account_device_id}_debt"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == 100.0


# ---------------------------------------------------------------------------
# Balance sensors — disabled by default (registered but not active)
# ---------------------------------------------------------------------------


async def test_account_balance_sensors_disabled_by_default(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that secondary balance sensors are registered but disabled by default."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    account_device_id = make_account_device_id(MOCK_LSPU_INFO_RESPONSE["account"])

    disabled_keys = [
        "balance_period",
        "balance_date",
        "balance_start",
        "balance_end",
        "charged_volume",
        "circulation",
        "forgiven_debt",
        "planned",
        "privilege",
        "privilege_volume",
        "restored_debt",
        "payment_adjustments",
        "end_balance_apgp",
        "prepayment_charged",
    ]

    for key in disabled_keys:
        entry = ent_reg.async_get(
            ent_reg.async_get_entity_id(
                "sensor", DOMAIN, f"{DOMAIN}_{account_device_id}_{key}"
            )
        )
        assert entry is not None, f"Entity {key} not registered"
        assert entry.disabled_by is not None, f"Entity {key} should be disabled"


async def test_account_balance_sensors_values_when_enabled(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test disabled balance sensors return correct values when manually enabled."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    account_device_id = make_account_device_id(MOCK_LSPU_INFO_RESPONSE["account"])
    balances = MOCK_LSPU_INFO_RESPONSE["balances"][0]

    sensors_to_check = {
        "balance_start": balances["balanceStartSum"],
        "balance_end": balances["balanceEndSum"],
        "charged_volume": balances["chargedVolume"],
        "circulation": balances["circulationSum"],
        "forgiven_debt": balances["forgivenDebt"],
        "planned": balances["plannedSum"],
        "privilege": balances["privilegeSum"],
        "privilege_volume": balances["privilegeVolume"],
        "restored_debt": balances["restoredDebt"],
        "payment_adjustments": balances["paymentAdjustments"],
        "end_balance_apgp": balances["endBalanceApgp"],
        "prepayment_charged": balances["prepaymentChargedAccumSum"],
    }

    for key, expected in sensors_to_check.items():
        unique_id = f"{DOMAIN}_{account_device_id}_{key}"
        entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None, f"Entity {key} not found"

        # Enable the entity
        ent_reg.async_update_entity(entity_id, disabled_by=None)

    # Reload to pick up enabled entities
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Trigger coordinator update to populate values
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    for key, expected in sensors_to_check.items():
        unique_id = f"{DOMAIN}_{account_device_id}_{key}"
        entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
        state = hass.states.get(entity_id)
        assert state is not None, f"State for {key} is None"
        assert float(state.state) == float(expected), (
            f"Sensor {key}: expected {expected}, got {state.state}"
        )


async def test_account_balance_period_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test balance_period (text) sensor value when enabled."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    account_device_id = make_account_device_id(MOCK_LSPU_INFO_RESPONSE["account"])

    entity_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{account_device_id}_balance_period"
    )
    assert entity_id is not None

    ent_reg.async_update_entity(entity_id, disabled_by=None)

    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "Январь 2026"


async def test_account_balance_date_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test balance_date sensor value when enabled."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    account_device_id = make_account_device_id(MOCK_LSPU_INFO_RESPONSE["account"])

    entity_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{account_device_id}_balance_date"
    )
    assert entity_id is not None

    ent_reg.async_update_entity(entity_id, disabled_by=None)

    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == str(date(2026, 1, 31))


# ---------------------------------------------------------------------------
# Balance sensors unavailable when balances is empty
# ---------------------------------------------------------------------------


async def test_account_balance_sensors_unavailable_no_balances(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test balance sensors are unavailable when balances array is empty."""
    mock_api.async_get_lspu_info = AsyncMock(return_value=MOCK_LSPU_INFO_NO_BALANCES)
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    account_device_id = make_account_device_id(MOCK_LSPU_INFO_RESPONSE["account"])

    for key in ("charged", "paid", "debt"):
        entity_id = ent_reg.async_get_entity_id(
            "sensor", DOMAIN, f"{DOMAIN}_{account_device_id}_{key}"
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == "unavailable"
