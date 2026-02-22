"""MyGas Sensor definitions."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MyGasConfigEntry
from .const import ATTR_LAST_UPDATE_TIME
from .coordinator import MyGasCoordinator
from .entity import (
    MyGasAccountCoordinatorEntity,
    MyGasBaseCoordinatorEntity,
    MyGasSensorEntityDescription,
    MyGasServiceCoordinatorEntity,
)
from .helpers import (
    to_date,
    to_float,
    to_str,
    make_account_device_id,
    make_device_id,
    make_entity_unique_id,
    make_service_device_id,
)

SENSOR_TYPES: tuple[MyGasSensorEntityDescription, ...] = (
    MyGasSensorEntityDescription(
        key="account",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: to_str(device.get_lspu_account_data().get("account")),
        available_fn=lambda device: "account" in device.get_lspu_account_data(),
        translation_key="account",
        attr_fn=lambda device: {
            parameter["name"]: parameter["value"]
            for parameter in device.get_lspu_account_data().get("parameters", {})
        },
    ),
    MyGasSensorEntityDescription(
        key="balance",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            device.get_lspu_account_data().get("balance")
        ),
        available_fn=lambda device: "balance" in device.get_lspu_account_data(),
        translation_key="balance",
    ),
    MyGasSensorEntityDescription(
        key="charged",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("chargedSum")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="charged",
    ),
    MyGasSensorEntityDescription(
        key="paid",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("paidSum")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="paid",
    ),
    MyGasSensorEntityDescription(
        key="debt",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("debtSum")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="debt",
    ),
    MyGasSensorEntityDescription(
        key="balance_period",
        value_fn=lambda device: to_str(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("name")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="balance_period",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="balance_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda device: to_date(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("date"),
            "%Y-%m-%d",
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="balance_date",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="balance_start",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("balanceStartSum")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="balance_start",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="balance_end",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("balanceEndSum")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="balance_end",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="charged_volume",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.GAS,
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("chargedVolume")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="charged_volume",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="circulation",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("circulationSum")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="circulation",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="forgiven_debt",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("forgivenDebt")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="forgiven_debt",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="planned",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("plannedSum")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="planned",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="privilege",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("privilegeSum")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="privilege",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="privilege_volume",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.GAS,
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("privilegeVolume")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="privilege_volume",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="restored_debt",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("restoredDebt")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="restored_debt",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="payment_adjustments",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("paymentAdjustments")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="payment_adjustments",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="end_balance_apgp",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("endBalanceApgp")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="end_balance_apgp",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="prepayment_charged",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: to_float(
            (device.get_lspu_account_data().get("balances") or [{}])[0].get("prepaymentChargedAccumSum")
        ),
        available_fn=lambda device: bool(device.get_lspu_account_data().get("balances")),
        translation_key="prepayment_charged",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="current_timestamp",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda device: device.coordinator.data.get(ATTR_LAST_UPDATE_TIME),
        available_fn=lambda device: ATTR_LAST_UPDATE_TIME in device.coordinator.data,
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="current_timestamp",
    ),
    MyGasSensorEntityDescription(
        key="counter",
        value_fn=lambda device: device.get_counter_data().get("name"),
        available_fn=lambda device: "name" in device.get_counter_data(),
        translation_key="counter",
        entity_category=EntityCategory.DIAGNOSTIC,
        attr_fn=lambda device: device.get_counter_attr(),
    ),
    MyGasSensorEntityDescription(
        key="average_rate",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.GAS,
        value_fn=lambda device: to_float(device.get_counter_data().get("averageRate")),
        available_fn=lambda device: "averageRate" in device.get_counter_data(),
        translation_key="average_rate",
    ),
    MyGasSensorEntityDescription(
        key="price",
        native_unit_of_measurement="RUB/m\u00b3",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda device: to_float(
            device.get_counter_data().get("price", {}).get("day")
        ),
        available_fn=lambda device: "price" in device.get_counter_data(),
        translation_key="price",
    ),
    MyGasSensorEntityDescription(
        key="price_middle",
        native_unit_of_measurement="RUB/m\u00b3",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda device: to_float(
            device.get_counter_data().get("price", {}).get("middle")
        ),
        available_fn=lambda device: "price" in device.get_counter_data(),
        translation_key="price_middle",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="price_night",
        native_unit_of_measurement="RUB/m\u00b3",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda device: to_float(
            device.get_counter_data().get("price", {}).get("night")
        ),
        available_fn=lambda device: "price" in device.get_counter_data(),
        translation_key="price_night",
        entity_registry_enabled_default=False,
    ),
    MyGasSensorEntityDescription(
        key="readings_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda device: to_date(
            device.get_latest_readings().get("date"), "%Y-%m-%dT%H:%M:%S"
        ),
        available_fn=lambda device: "date" in device.get_latest_readings(),
        translation_key="readings_date",
    ),
    MyGasSensorEntityDescription(
        key="readings",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.GAS,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda device: to_float(device.get_latest_readings().get("valueDay")),
        available_fn=lambda device: "valueDay" in device.get_latest_readings(),
        translation_key="readings",
    ),
    MyGasSensorEntityDescription(
        key="consumption",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.GAS,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda device: to_float(device.get_latest_readings().get("rate")),
        available_fn=lambda device: "rate" in device.get_latest_readings(),
        translation_key="consumption",
    ),
)

_ACCOUNT_SENSOR_KEYS = {
    "account", "balance", "charged", "paid", "debt",
    "balance_period", "balance_date", "balance_start", "balance_end",
    "charged_volume", "circulation", "forgiven_debt", "planned",
    "privilege", "privilege_volume", "restored_debt",
    "payment_adjustments", "end_balance_apgp", "prepayment_charged",
    "current_timestamp",
}

ACCOUNT_SENSOR_TYPES: tuple[MyGasSensorEntityDescription, ...] = tuple(
    desc for desc in SENSOR_TYPES if desc.key in _ACCOUNT_SENSOR_KEYS
)

_MULTI_TARIFF_SENSOR_KEYS = {"price_middle", "price_night"}

COUNTER_SENSOR_TYPES: tuple[MyGasSensorEntityDescription, ...] = tuple(
    desc for desc in SENSOR_TYPES
    if desc.key not in _ACCOUNT_SENSOR_KEYS and desc.key not in _MULTI_TARIFF_SENSOR_KEYS
)

MULTI_TARIFF_SENSOR_TYPES: tuple[MyGasSensorEntityDescription, ...] = tuple(
    desc for desc in SENSOR_TYPES if desc.key in _MULTI_TARIFF_SENSOR_KEYS
)


class MyGasAccountSensorEntity(MyGasAccountCoordinatorEntity, SensorEntity):
    """MyGas Account-level Sensor Entity."""

    entity_description: MyGasSensorEntityDescription

    def __init__(
        self,
        coordinator: MyGasCoordinator,
        entity_description: MyGasSensorEntityDescription,
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

    @property
    def available(self) -> bool:
        """Return True if sensor is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.entity_description.available_fn(self)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.entity_description.value_fn(self)
        self._attr_extra_state_attributes = self.entity_description.attr_fn(self)
        super()._handle_coordinator_update()


class MyGasCounterCoordinatorEntity(MyGasBaseCoordinatorEntity, SensorEntity):
    """MyGas Counter Entity."""

    entity_description: MyGasSensorEntityDescription

    def __init__(
        self,
        coordinator: MyGasCoordinator,
        entity_description: MyGasSensorEntityDescription,
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

    @property
    def available(self) -> bool:
        """Return True if sensor is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.entity_description.available_fn(self)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.entity_description.value_fn(self)
        self._attr_extra_state_attributes = self.entity_description.attr_fn(self)
        super()._handle_coordinator_update()


class MyGasServiceBalanceSensorEntity(MyGasServiceCoordinatorEntity, SensorEntity):
    """MyGas Service balance Sensor Entity."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "RUB"
    _attr_translation_key = "service_balance"

    def __init__(
        self,
        coordinator: MyGasCoordinator,
        account_id: int,
        lspu_account_id: int,
        service_id: int,
    ) -> None:
        """Initialize the Entity."""
        super().__init__(coordinator, account_id, lspu_account_id, service_id)

        service = coordinator.get_services(account_id, lspu_account_id)[service_id]
        account_number = coordinator.get_account_number(account_id, lspu_account_id)
        device_identifier = make_service_device_id(account_number, service["id"])
        self._attr_unique_id = make_entity_unique_id(
            device_identifier, "service_balance"
        )

    @property
    def available(self) -> bool:
        """Return True if sensor is available."""
        return super().available and self.coordinator.data is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        service = self.get_service_data()
        self._attr_native_value = to_float(service.get("balance"))
        super()._handle_coordinator_update()


class MyGasServiceTariffSensorEntity(MyGasServiceCoordinatorEntity, SensorEntity):
    """MyGas Service tariff rate Sensor Entity."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "RUB"

    def __init__(
        self,
        coordinator: MyGasCoordinator,
        account_id: int,
        lspu_account_id: int,
        service_id: int,
        child_id: int,
    ) -> None:
        """Initialize the Entity."""
        super().__init__(coordinator, account_id, lspu_account_id, service_id)
        self.child_id = child_id

        service = coordinator.get_services(account_id, lspu_account_id)[service_id]
        child = service["children"][child_id]

        account_number = coordinator.get_account_number(account_id, lspu_account_id)
        device_identifier = make_service_device_id(account_number, service["id"])
        self._attr_unique_id = make_entity_unique_id(
            device_identifier, f"service_tariff_{child_id}"
        )
        self._attr_translation_key = "service_tariff"
        self._attr_name = child["name"]

    @property
    def available(self) -> bool:
        """Return True if sensor is available."""
        return super().available and self.coordinator.data is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        child = self.get_child_data(self.child_id)
        self._attr_native_value = to_float(child.get("tariff"))
        self._attr_extra_state_attributes = {
            "Норматив потребления": to_float(child.get("norm")),
            "Цена за м\u00b3": to_float(child.get("price")),
            "Дата начала": to_date(child.get("startDate"), "%Y-%m-%dT%H:%M:%S"),
        }
        super()._handle_coordinator_update()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MyGasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a config entry."""
    coordinator = entry.runtime_data

    entities: list[
        MyGasAccountSensorEntity
        | MyGasCounterCoordinatorEntity
        | MyGasServiceBalanceSensorEntity
        | MyGasServiceTariffSensorEntity
    ] = []
    for account_id in coordinator.get_accounts():
        for lspu_account_id in range(len(coordinator.get_lspu_accounts(account_id))):
            # Account-level sensors (always created)
            entities.extend(
                MyGasAccountSensorEntity(
                    coordinator,
                    entity_description,
                    account_id,
                    lspu_account_id,
                )
                for entity_description in ACCOUNT_SENSOR_TYPES
            )
            # Counter-level sensors
            counters = coordinator.get_counters(account_id, lspu_account_id)
            for counter_id, counter in enumerate(counters):
                entities.extend(
                    MyGasCounterCoordinatorEntity(
                        coordinator,
                        entity_description,
                        account_id,
                        lspu_account_id,
                        counter_id,
                    )
                    for entity_description in COUNTER_SENSOR_TYPES
                )
                # Multi-tariff sensors (only for numberOfRates > 1)
                if counter.get("numberOfRates", 1) > 1:
                    entities.extend(
                        MyGasCounterCoordinatorEntity(
                            coordinator,
                            entity_description,
                            account_id,
                            lspu_account_id,
                            counter_id,
                        )
                        for entity_description in MULTI_TARIFF_SENSOR_TYPES
                    )
            # Service-level sensors
            services = coordinator.get_services(account_id, lspu_account_id)
            for service_idx, service in enumerate(services):
                # Balance sensor (always created for each service)
                entities.append(
                    MyGasServiceBalanceSensorEntity(
                        coordinator,
                        account_id,
                        lspu_account_id,
                        service_idx,
                    )
                )
                # Tariff rate sensors (one per child)
                for child_idx in range(len(service.get("children", []))):
                    entities.append(
                        MyGasServiceTariffSensorEntity(
                            coordinator,
                            account_id,
                            lspu_account_id,
                            service_idx,
                            child_idx,
                        )
                    )

    async_add_entities(entities, True)
