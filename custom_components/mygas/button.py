"""Support for MyGas button."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import (
    ENTITY_ID_FORMAT,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, ATTR_IDENTIFIERS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory, async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import DOMAIN, SERVICE_GET_BILL, SERVICE_REFRESH
from .coordinator import MyGasCoordinator
from .entity import MyGasBaseCoordinatorEntity


@dataclass(kw_only=True, frozen=True)
class MyGasButtonRequiredKeysMixin:
    """Mixin for required keys."""

    async_press: Callable[[MyGasCoordinator, str], Awaitable]


@dataclass(kw_only=True, frozen=True)
class MyGasButtonEntityDescription(
    ButtonEntityDescription, MyGasButtonRequiredKeysMixin
):
    """Class describing MyGas button entities."""


BUTTON_DESCRIPTIONS: tuple[MyGasButtonEntityDescription, ...] = (
    MyGasButtonEntityDescription(
        key="refresh",
        icon="mdi:refresh",
        name="Обновить сведения",
        entity_category=EntityCategory.DIAGNOSTIC,
        async_press=lambda coordinator, device_id: coordinator.hass.services.async_call(
            DOMAIN, SERVICE_REFRESH, {ATTR_DEVICE_ID: device_id}, blocking=True
        ),
        translation_key="refresh",
    ),
    MyGasButtonEntityDescription(
        key="get_bill",
        icon="mdi:receipt-text-outline",
        name="Получить счет",
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
        # Safely get identifiers from device_info (device_info may be None
        # and 'identifiers' is not a required TypedDict key)
        identifiers = (self.device_info or {}).get(ATTR_IDENTIFIERS, set())
        first_identifier = next(iter(identifiers), ())
        ids = [*list(first_identifier), entity_description.key]
        # Ensure all parts are strings before joining
        self._attr_unique_id = slugify("_".join(str(part) for part in ids))
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self.unique_id, hass=coordinator.hass
        )

    async def async_press(self) -> None:
        """Press the button."""
        if not self.registry_entry:
            return
        if device_id := self.registry_entry.device_id:
            await self.entity_description.async_press(self.coordinator, device_id)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a config entry."""

    coordinator: MyGasCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[MyGasButtonEntity] = []

    for account_id in coordinator.get_accounts():
        for lspu_account_id in range(len(coordinator.get_lspu_accounts(account_id))):
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
