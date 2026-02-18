"""Base entity for MyGas integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import aiomygas

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.const import ATTR_MODEL, ATTR_NAME
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ACCOUNT_MODEL,
    ATTR_SERIAL_NUM,
    ATTR_UUID,
    ATTRIBUTION,
    CONFIGURATION_URL,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import MyGasCoordinator
from .helpers import to_date, to_int, to_str, make_account_device_id, make_device_id


class MyGasCoordinatorEntity(CoordinatorEntity[MyGasCoordinator]):
    """Common base for all MyGas entities."""

    coordinator: MyGasCoordinator
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MyGasCoordinator,
        account_id: int,
        lspu_account_id: int,
    ) -> None:
        """Initialize the Entity."""
        super().__init__(coordinator)
        self.account_id = account_id
        self.lspu_account_id = lspu_account_id

    def get_lspu_account_data(self) -> dict[str | int, Any]:
        """Get LSPU account data."""
        return self.coordinator.get_lspu_accounts(self.account_id)[self.lspu_account_id]


@dataclass(frozen=True, kw_only=True)
class MyGasSensorEntityDescription(SensorEntityDescription):
    """Describes MyGas sensor entity."""

    value_fn: Callable[[MyGasCoordinatorEntity], StateType | datetime | date]
    attr_fn: Callable[
        [MyGasCoordinatorEntity], dict[str, StateType | datetime | date]
    ] = lambda _: {}
    available_fn: Callable[[MyGasCoordinatorEntity], bool] = lambda _: True


class MyGasAccountCoordinatorEntity(MyGasCoordinatorEntity):
    """MyGas Account-level Entity (no counter)."""

    def __init__(
        self,
        coordinator: MyGasCoordinator,
        account_id: int,
        lspu_account_id: int,
    ) -> None:
        """Initialize the Entity."""
        super().__init__(coordinator, account_id, lspu_account_id)

        account_number = coordinator.get_account_number(
            self.account_id, self.lspu_account_id
        )
        account_alias = coordinator.get_account_alias(
            self.account_id, self.lspu_account_id
        )

        if account_alias:
            device_name = f"ЛС {account_number} ({account_alias})"
        else:
            device_name = f"ЛС {account_number}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, make_account_device_id(account_number))},
            manufacturer=MANUFACTURER,
            model=ACCOUNT_MODEL,
            name=device_name,
            sw_version=aiomygas.__version__,
            configuration_url=CONFIGURATION_URL,
        )


class MyGasBaseCoordinatorEntity(MyGasCoordinatorEntity):
    """MyGas Counter-level Entity."""

    def __init__(
        self,
        coordinator: MyGasCoordinator,
        account_id: int,
        lspu_account_id: int,
        counter_id: int,
    ) -> None:
        """Initialize the Entity."""
        super().__init__(coordinator, account_id, lspu_account_id)
        self.counter_id = counter_id

        counter = coordinator.get_counters(self.account_id, self.lspu_account_id)[
            counter_id
        ]

        account_number = coordinator.get_account_number(
            self.account_id, self.lspu_account_id
        )

        device_id = make_device_id(account_number, counter[ATTR_UUID])

        account_alias = coordinator.get_account_alias(
            self.account_id, self.lspu_account_id
        )
        if account_alias:
            device_name = f"{counter[ATTR_NAME]} ({account_alias})"
        else:
            device_name = f"{counter[ATTR_NAME]}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            via_device=(DOMAIN, make_account_device_id(account_number)),
            manufacturer=MANUFACTURER,
            model=counter[ATTR_MODEL],
            name=device_name,
            serial_number=counter[ATTR_SERIAL_NUM],
            sw_version=aiomygas.__version__,
            configuration_url=CONFIGURATION_URL,
        )

    def get_counter_data(self) -> dict[str, Any]:
        """Get counter data."""
        return self.coordinator.get_counters(self.account_id, self.lspu_account_id)[
            self.counter_id
        ]

    def get_latest_readings(self) -> dict[str, Any]:
        """Latest readings for counter."""
        counter = self.coordinator.get_counters(self.account_id, self.lspu_account_id)[
            self.counter_id
        ]
        values = counter.get("values", [])
        return values[0] if values else {}

    def get_counter_attr(self) -> dict[str, Any]:
        """Get counter attr."""
        counter = self.coordinator.get_counters(self.account_id, self.lspu_account_id)[
            self.counter_id
        ]
        return {
            "Модель": to_str(counter.get("model")),
            "Серийный номер": to_str(counter.get("serialNumber")),
            "Состояние счетчика": to_str(counter.get("state")),
            "Тип оборудования": to_str(counter.get("equipmentKind")),
            "Расположение": to_str(counter.get("position")),
            "Ресурс": to_str(counter.get("serviceName")),
            "Тарифность": to_int(counter.get("numberOfRates")),
            "Дата очередной поверки": to_date(
                counter.get("checkDate"), "%Y-%m-%dT%H:%M:%S"
            ),
            "Плановая дата ТО": to_date(
                counter.get("techSupportDate"), "%Y-%m-%dT%H:%M:%S"
            ),
            "Дата установки пломбы": to_date(
                counter.get("sealDate"), "%Y-%m-%dT%H:%M:%S"
            ),
            "Дата заводской пломбы": to_date(
                counter.get("factorySealDate"), "%Y-%m-%dT%H:%M:%S"
            ),
            "Дата изготовления прибора": to_date(
                counter.get("commissionedOn"), "%Y-%m-%dT%H:%M:%S"
            ),
        }
