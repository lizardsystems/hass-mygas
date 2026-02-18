"""Support for MyGas button."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MyGasConfigEntry
from .const import DOMAIN, SERVICE_GET_BILL, SERVICE_REFRESH
from .coordinator import MyGasCoordinator
from .entity import MyGasAccountCoordinatorEntity, MyGasBaseCoordinatorEntity
from .helpers import make_account_device_id, make_device_id, make_entity_unique_id


@dataclass(kw_only=True, frozen=True)
class MyGasButtonEntityDescription(ButtonEntityDescription):
    """Class describing MyGas button entities."""

    async_press: Callable[[MyGasCoordinator, str], Awaitable]


BUTTON_DESCRIPTIONS: tuple[MyGasButtonEntityDescription, ...] = (
    MyGasButtonEntityDescription(
        key="refresh",
        entity_category=EntityCategory.DIAGNOSTIC,
        async_press=lambda coordinator, device_id: coordinator.hass.services.async_call(
            DOMAIN, SERVICE_REFRESH, {ATTR_DEVICE_ID: device_id}, blocking=True
        ),
        translation_key="refresh",
    ),
    MyGasButtonEntityDescription(
        key="get_bill",
        entity_category=EntityCategory.DIAGNOSTIC,
        async_press=lambda coordinator, device_id: coordinator.hass.services.async_call(
            DOMAIN, SERVICE_GET_BILL, {ATTR_DEVICE_ID: device_id}, blocking=True
        ),
        translation_key="get_bill",
    ),
)


class MyGasButtonEntity(MyGasBaseCoordinatorEntity, ButtonEntity):
    """Representation of a MyGas button."""

    entity_description: MyGasButtonEntityDescription

    def __init__(
        self,
        coordinator: MyGasCoordinator,
        entity_description: MyGasButtonEntityDescription,
        account_id: int,
        lspu_group_id: int,
        counter_id: int,
    ) -> None:
        """Initialize the Entity."""
        super().__init__(coordinator, account_id, lspu_group_id, counter_id)
        self.entity_description = entity_description
        account_number = coordinator.get_account_number(account_id, lspu_group_id)
        counter_uuid = coordinator.get_counters(account_id, lspu_group_id)[counter_id].get("uuid", "")
        self._attr_unique_id = make_entity_unique_id(
            make_device_id(account_number, counter_uuid), entity_description.key
        )

    async def async_press(self) -> None:
        """Press the button."""
        if not self.registry_entry:
            return
        if device_id := self.registry_entry.device_id:
            await self.entity_description.async_press(self.coordinator, device_id)


class MyGasAccountButtonEntity(MyGasAccountCoordinatorEntity, ButtonEntity):
    """Representation of a MyGas account-level button."""

    entity_description: MyGasButtonEntityDescription

    def __init__(
        self,
        coordinator: MyGasCoordinator,
        entity_description: MyGasButtonEntityDescription,
        account_id: int,
        lspu_account_id: int,
    ) -> None:
        """Initialize the Entity."""
        super().__init__(coordinator, account_id, lspu_account_id)
        self.entity_description = entity_description
        account_number = coordinator.get_account_number(account_id, lspu_account_id)
        self._attr_unique_id = make_entity_unique_id(
            make_account_device_id(account_number), entity_description.key
        )

    async def async_press(self) -> None:
        """Press the button."""
        if not self.registry_entry:
            return
        if device_id := self.registry_entry.device_id:
            await self.entity_description.async_press(self.coordinator, device_id)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MyGasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a config entry."""
    coordinator = entry.runtime_data
    entities: list[MyGasAccountButtonEntity | MyGasButtonEntity] = []

    for account_id in coordinator.get_accounts():
        for lspu_account_id in range(len(coordinator.get_lspu_accounts(account_id))):
            # Account-level buttons (always created)
            entities.extend(
                MyGasAccountButtonEntity(
                    coordinator,
                    entity_description,
                    account_id,
                    lspu_account_id,
                )
                for entity_description in BUTTON_DESCRIPTIONS
            )
            # Counter-level buttons
            for counter_id in range(
                len(coordinator.get_counters(account_id, lspu_account_id))
            ):
                entities.extend(
                    MyGasButtonEntity(
                        coordinator,
                        entity_description,
                        account_id,
                        lspu_account_id,
                        counter_id,
                    )
                    for entity_description in BUTTON_DESCRIPTIONS
                )

    async_add_entities(entities, True)
