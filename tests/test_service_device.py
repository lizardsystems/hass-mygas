"""Tests for service-level devices and sensors."""
from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mygas.const import DOMAIN, SERVICE_MODEL
from custom_components.mygas.helpers import (
    make_account_device_id,
    make_entity_unique_id,
    make_service_device_id,
)

from .const import MOCK_LSPU_INFO_RESPONSE


# Response with no services
MOCK_LSPU_INFO_NO_SERVICES = {
    **MOCK_LSPU_INFO_RESPONSE,
    "services": [],
}

# Response without services key
MOCK_LSPU_INFO_MISSING_SERVICES = {
    k: v for k, v in MOCK_LSPU_INFO_RESPONSE.items() if k != "services"
}

ACCOUNT_NUMBER = MOCK_LSPU_INFO_RESPONSE["account"]
SERVICES = MOCK_LSPU_INFO_RESPONSE["services"]


# ---------------------------------------------------------------------------
# Service device creation
# ---------------------------------------------------------------------------


async def test_service_devices_created(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that a device is created for each service."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    device_registry = dr.async_get(hass)

    for service in SERVICES:
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, make_service_device_id(ACCOUNT_NUMBER, service["id"]))}
        )
        assert device is not None, f"Device for service {service['name']} not created"
        assert device.name == service["name"]
        assert device.model == SERVICE_MODEL


async def test_service_device_via_device(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that service devices link to the account device via via_device."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)

    account_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_account_device_id(ACCOUNT_NUMBER))}
    )
    assert account_device is not None

    service = SERVICES[0]
    service_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_service_device_id(ACCOUNT_NUMBER, service["id"]))}
    )
    assert service_device is not None
    assert service_device.via_device_id == account_device.id


async def test_no_service_devices_when_no_services(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that no service devices are created when services list is empty."""
    mock_api.async_get_lspu_info = AsyncMock(return_value=MOCK_LSPU_INFO_NO_SERVICES)
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )
    # Only account device + counter device
    assert len(devices) == 2


async def test_no_service_devices_when_services_key_missing(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test graceful handling when services key is absent from API response."""
    mock_api.async_get_lspu_info = AsyncMock(
        return_value=MOCK_LSPU_INFO_MISSING_SERVICES
    )
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    device_registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )
    # Only account device + counter device
    assert len(devices) == 2


# ---------------------------------------------------------------------------
# Device count
# ---------------------------------------------------------------------------


async def test_total_device_count(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test total number of devices: 1 account + 1 counter + 3 services."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )
    # 1 account + 1 counter + 3 services = 5
    assert len(devices) == 5


# ---------------------------------------------------------------------------
# Balance sensor
# ---------------------------------------------------------------------------


async def test_service_balance_sensor_created(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that a balance sensor is created for each service."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)

    for service in SERVICES:
        device_identifier = make_service_device_id(ACCOUNT_NUMBER, service["id"])
        unique_id = make_entity_unique_id(device_identifier, "service_balance")
        entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None, (
            f"Balance sensor not created for service {service['name']}"
        )


async def test_service_balance_sensor_values(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that balance sensor values match API data."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)

    expected = {
        "02": -6.32,
        "04": -3.69,
        "61": 0.0,
    }

    for service in SERVICES:
        device_identifier = make_service_device_id(ACCOUNT_NUMBER, service["id"])
        unique_id = make_entity_unique_id(device_identifier, "service_balance")
        entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)

        state = hass.states.get(entity_id)
        assert state is not None, f"No state for service {service['name']}"
        assert float(state.state) == expected[service["id"]], (
            f"Service {service['name']}: expected {expected[service['id']]}, "
            f"got {state.state}"
        )


# ---------------------------------------------------------------------------
# Tariff sensors
# ---------------------------------------------------------------------------


async def test_tariff_sensors_created_for_children(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that tariff sensors are created for each child of a service."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)

    # Service "02" has 2 children
    device_identifier = make_service_device_id(ACCOUNT_NUMBER, "02")
    for child_idx in range(2):
        unique_id = make_entity_unique_id(
            device_identifier, f"service_tariff_{child_idx}"
        )
        entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None, (
            f"Tariff sensor {child_idx} not created for service 02"
        )


async def test_no_tariff_sensors_for_childless_services(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that no tariff sensors are created for services with empty children."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)

    # Services "04" and "61" have no children
    for service_id in ("04", "61"):
        device_identifier = make_service_device_id(ACCOUNT_NUMBER, service_id)
        unique_id = make_entity_unique_id(device_identifier, "service_tariff_0")
        entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is None, (
            f"Tariff sensor should not exist for childless service {service_id}"
        )


async def test_tariff_sensor_values(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that tariff sensor values match child tariff from API data."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    device_identifier = make_service_device_id(ACCOUNT_NUMBER, "02")
    children = SERVICES[0]["children"]

    for child_idx, child in enumerate(children):
        unique_id = make_entity_unique_id(
            device_identifier, f"service_tariff_{child_idx}"
        )
        entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
        state = hass.states.get(entity_id)
        assert state is not None
        assert float(state.state) == child["tariff"]


async def test_tariff_sensor_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that tariff sensor has correct extra attributes."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    device_identifier = make_service_device_id(ACCOUNT_NUMBER, "02")
    unique_id = make_entity_unique_id(device_identifier, "service_tariff_0")
    entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)

    state = hass.states.get(entity_id)
    assert state is not None

    attrs = state.attributes
    child = SERVICES[0]["children"][0]
    assert attrs["Норматив потребления"] == child["norm"]
    assert attrs["Цена за м\u00b3"] == child["price"]


# ---------------------------------------------------------------------------
# Stale service device removal
# ---------------------------------------------------------------------------


async def test_stale_service_device_removed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that service devices for removed services are cleaned up."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)

    # Create a stale service device
    device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, make_service_device_id(ACCOUNT_NUMBER, "99"))},
    )
    stale_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_service_device_id(ACCOUNT_NUMBER, "99"))}
    )
    assert stale_device is not None

    # Reload triggers stale device cleanup
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    stale_device = device_registry.async_get_device(
        identifiers={(DOMAIN, make_service_device_id(ACCOUNT_NUMBER, "99"))}
    )
    assert stale_device is None

    # Real service devices should still exist
    for service in SERVICES:
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, make_service_device_id(ACCOUNT_NUMBER, service["id"]))}
        )
        assert device is not None


async def test_service_devices_kept_on_reload(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_auth: AsyncMock,
    mock_api: AsyncMock,
) -> None:
    """Test that service devices survive config entry reload."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )
    # 1 account + 1 counter + 3 services = 5
    assert len(devices) == 5
