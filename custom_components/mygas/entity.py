"""Base entity for MyGas integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from aiomygas.const import APP_VERSION, MOBILE_APP_NAME

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.const import ATTR_MODEL, ATTR_NAME
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_SERIAL_NUM,
    ATTR_UUID,
    ATTRIBUTION,
    CONFIGURATION_URL,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import MyGasCoordinator
from .helpers import _to_date, _to_int, _to_str, make_device_id


@dataclass(frozen=True, kw_only=True)
class MyGasEntityDescriptionMixin:
    """Mixin for required MyGas base description keys."""

    value_fn: Callable[[MyGasBaseCoordinatorEntity], StateType | datetime | date]


@dataclass(frozen=True, kw_only=True)
class MyGasBaseSensorEntityDescription(SensorEntityDescription):
    """Describes MyGas sensor entity default overrides."""

    attr_fn: Callable[
        [MyGasBaseCoordinatorEntity], dict[str, StateType | datetime | date]
    ] = lambda _: {}
    avabl_fn: Callable[[MyGasBaseCoordinatorEntity], bool] = lambda _: True
    icon_fn: Callable[[MyGasBaseCoordinatorEntity], str | None] = lambda _: None


@dataclass(frozen=True, kw_only=True)
class MyGasSensorEntityDescription(
    MyGasBaseSensorEntityDescription, MyGasEntityDescriptionMixin
):
    """Describes MyGas sensor entity."""


class MyGasBaseCoordinatorEntity(CoordinatorEntity[MyGasCoordinator]):
    """MyGas Base Entity."""

    coordinator: MyGasCoordinator
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    account_id: int
    counter_id: int
    lspu_account_id: int

    def __init__(
        self,
        coordinator: MyGasCoordinator,
        account_id: int,
        lspu_account_id: int,
        counter_id: int,
    ) -> None:
        """Initialize the Entity."""
        super().__init__(coordinator)
        self.account_id = account_id
        self.lspu_account_id = lspu_account_id
        self.counter_id = counter_id

        counter = coordinator.get_counters(self.account_id, self.lspu_account_id)[
            counter_id
        ]

        device_id = make_device_id(
            coordinator.get_account_number(self.account_id, self.lspu_account_id),
            counter[ATTR_UUID],
        )

        account_alias = coordinator.get_account_alias(
            self.account_id, self.lspu_account_id
        )
        if account_alias:
            device_name = f"{counter[ATTR_NAME]} ({account_alias})"
        else:
            device_name = f"{counter[ATTR_NAME]}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            manufacturer=MANUFACTURER,
            model=counter[ATTR_MODEL],
            name=device_name,
            serial_number=counter[ATTR_SERIAL_NUM],
            sw_version=APP_VERSION[MOBILE_APP_NAME],
            configuration_url=CONFIGURATION_URL,
        )

    def get_lspu_account_data(self) -> dict[str | int, Any]:
        """Get LSPU account data."""
        return self.coordinator.get_lspu_accounts(self.account_id)[self.lspu_account_id]

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

    def get_counter_attr(self):
        """Get counter attr."""
        counter = self.coordinator.get_counters(self.account_id, self.lspu_account_id)[
            self.counter_id
        ]
        return {
            "Модель": _to_str(counter.get("model")),
            "Серийный номер": _to_str(counter.get("serialNumber")),
            "Состояние счетчика": _to_str(counter.get("state")),
            "Тип оборудования": _to_str(counter.get("equipmentKind")),
            "Расположение": _to_str(counter.get("position")),
            "Ресурс": _to_str(counter.get("serviceName")),
            "Тарифность": _to_int(counter.get("numberOfRates")),
            "Дата очередной поверки": _to_date(
                counter.get("checkDate"), "%Y-%m-%dT%H:%M:%S"
            ),
            "Плановая дата ТО": _to_date(
                counter.get("techSupportDate"), "%Y-%m-%dT%H:%M:%S"
            ),
            "Дата установки пломбы": _to_date(
                counter.get("sealDate"), "%Y-%m-%dT%H:%M:%S"
            ),
            "Дата заводской пломбы": _to_date(
                counter.get("factorySealDate"), "%Y-%m-%dT%H:%M:%S"
            ),
            "Дата изготовления прибора": _to_date(
                counter.get("commissionedOn"), "%Y-%m-%dT%H:%M:%S"
            ),
        }
