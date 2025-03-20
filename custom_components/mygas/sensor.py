"""MyGas Sensor definitions."""
from __future__ import annotations

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_IDENTIFIERS, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory, async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import (
    ATTR_LAST_UPDATE_TIME,
    DOMAIN,
)
from .coordinator import MyGasCoordinator
from .entity import MyGasBaseCoordinatorEntity, MyGasSensorEntityDescription
from .helpers import _to_date, _to_float, _to_str

SENSOR_TYPES: tuple[MyGasSensorEntityDescription, ...] = (
    # Информация по счету
    MyGasSensorEntityDescription(
        key="account",
        name="Лицевой счет",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: _to_str(device.get_lspu_account_data().get("account")),
        avabl_fn=lambda device: "account" in device.get_lspu_account_data(),
        translation_key="account",
        attr_fn=lambda device: {
            parameter["name"]: parameter["value"]
            for parameter in device.get_lspu_account_data().get("parameters", {})
        },
    ),
    MyGasSensorEntityDescription(
        key="balance",
        name="Задолженность",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="RUB",
        value_fn=lambda device: _to_float(
            device.get_lspu_account_data().get("balance")
        ),
        avabl_fn=lambda device: "balance" in device.get_lspu_account_data(),
        translation_key="balance",
    ),
    MyGasSensorEntityDescription(
        key="current_timestamp",
        name="Последнее обновление",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda device: device.coordinator.data.get(ATTR_LAST_UPDATE_TIME),
        avabl_fn=lambda device: ATTR_LAST_UPDATE_TIME in device.coordinator.data,
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="current_timestamp",
    ),
    MyGasSensorEntityDescription(
        key="counter",
        name="Счетчик",
        icon="mdi:counter",
        value_fn=lambda device: device.get_counter_data().get("name"),
        avabl_fn=lambda device: "name" in device.get_counter_data(),
        translation_key="counter",
        entity_category=EntityCategory.DIAGNOSTIC,
        attr_fn=lambda device: device.get_counter_attr(),
    ),
    MyGasSensorEntityDescription(
        key="average_rate",
        name="Средний расход",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.GAS,
        # state_class=SensorStateClass.TOTAL,
        value_fn=lambda device: _to_float(device.get_counter_data().get("averageRate")),
        avabl_fn=lambda device: "averageRate" in device.get_counter_data(),
        translation_key="average_rate",
    ),
    MyGasSensorEntityDescription(
        key="price",
        name="Цена за м³",
        native_unit_of_measurement="RUB/m³",
        device_class=SensorDeviceClass.MONETARY,
        # state_class=SensorStateClass.TOTAL,
        value_fn=lambda device: _to_float(
            device.get_counter_data().get("price", {}).get("day")
        ),
        avabl_fn=lambda device: "price" in device.get_counter_data(),
        translation_key="price",
    ),
    MyGasSensorEntityDescription(
        key="readings_date",
        name="Дата показаний",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda device: _to_date(
            device.get_latest_readings().get("date"), "%Y-%m-%dT%H:%M:%S"
        ),
        avabl_fn=lambda device: "date" in device.get_latest_readings(),
        translation_key="readings_date",
    ),
    MyGasSensorEntityDescription(
        key="readings",
        name="Показания",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.GAS,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda device: _to_float(device.get_latest_readings().get("valueDay")),
        avabl_fn=lambda device: "valueDay" in device.get_latest_readings(),
        translation_key="readings",
    ),
    MyGasSensorEntityDescription(
        key="consumption",
        name="Потребление",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.GAS,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda device: _to_float(device.get_latest_readings().get("rate")),
        avabl_fn=lambda device: "rate" in device.get_latest_readings(),
        translation_key="consumption",
    ),
)


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
        ids = list(next(iter(self.device_info[ATTR_IDENTIFIERS]))) + [
            entity_description.key
        ]
        self._attr_unique_id = slugify("_".join(ids))

        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, self.unique_id, hass=coordinator.hass
        )

    @property
    def available(self) -> bool:
        """Return True if sensor is available."""
        return (
                super().available
                and self.coordinator.data is not None
                and self.entity_description.avabl_fn(self)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.entity_description.value_fn(self)
        self._attr_extra_state_attributes = self.entity_description.attr_fn(self)
        if self.entity_description.icon_fn is not None:
            self._attr_icon = self.entity_description.icon_fn(self)

        self.coordinator.logger.debug(
            "Entity ID: %s Value: %s", self.entity_id, self.native_value
        )

        super()._handle_coordinator_update()


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a config entry."""

    coordinator: MyGasCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[MyGasCounterCoordinatorEntity] = []
    for account_id in coordinator.get_accounts():
        for lspu_account_id in range(len(coordinator.get_lspu_accounts(account_id))):
            for counter_id in range(
                    len(coordinator.get_counters(account_id, lspu_account_id))
            ):
                for entity_description in SENSOR_TYPES:
                    entities.append(
                        MyGasCounterCoordinatorEntity(
                            coordinator,
                            entity_description,
                            account_id,
                            lspu_account_id,
                            counter_id,
                        )
                    )

    async_add_entities(entities, True)
