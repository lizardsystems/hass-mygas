"""MyGas services."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from typing import Any
from urllib.parse import unquote

import voluptuous as vol

from homeassistant.const import ATTR_DATE, ATTR_DEVICE_ID, CONF_ERROR, CONF_URL
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import verify_domain_control

from .const import (
    ATTR_COUNTERS,
    ATTR_EMAIL,
    ATTR_MESSAGE,
    ATTR_READINGS,
    ATTR_SENT,
    ATTR_VALUE,
    DOMAIN,
    SERVICE_GET_BILL,
    SERVICE_REFRESH,
    SERVICE_SEND_READINGS,
)
from .coordinator import MyGasCoordinator
from .helpers import async_get_coordinator, get_bill_date, get_float_value, get_previous_month

_LOGGER = logging.getLogger(__name__)

SERVICE_BASE_SCHEMA = {vol.Required(ATTR_DEVICE_ID): cv.string}

SERVICE_REFRESH_SCHEMA = vol.Schema(
    {
        **SERVICE_BASE_SCHEMA,
    }
)

SERVICE_SEND_READINGS_SCHEMA = vol.Schema(
    vol.All(
        {
            **SERVICE_BASE_SCHEMA,
            vol.Required(ATTR_VALUE): cv.entity_id,
        }
    ),
)

SERVICE_GET_BILL_SCHEMA = vol.Schema(
    {
        **SERVICE_BASE_SCHEMA,
        vol.Optional(ATTR_DATE): cv.date,
        vol.Optional(ATTR_EMAIL): vol.Email(),
    },
)


@dataclass
class ServiceDescription:
    """A class that describes MyGas services."""

    name: str
    service_func: Callable[
        [HomeAssistant, ServiceCall, MyGasCoordinator], Awaitable[dict[str, Any]]
    ]
    schema: vol.Schema | None = None


async def _async_handle_refresh(
    hass: HomeAssistant, service_call: ServiceCall, coordinator: MyGasCoordinator
) -> dict[str, Any]:
    await coordinator.async_refresh()
    return {}


async def _async_handle_send_readings(
    hass: HomeAssistant, service_call: ServiceCall, coordinator: MyGasCoordinator
) -> dict[str, Any]:
    value = int(
        round(
            get_float_value(hass, service_call.data.get(ATTR_VALUE)) + 0.5
        )  # round to greater integer
    )
    device_id = service_call.data.get(ATTR_DEVICE_ID)
    result = await coordinator.async_send_readings(device_id, value)

    if result is None:
        raise HomeAssistantError(f"{service_call.service}: Empty response from API.")

    if not isinstance(result, list) or len(result) == 0:
        raise HomeAssistantError(
            f"{service_call.service}: Unrecognised response from API: {result}"
        )

    counters = result[0].get(ATTR_COUNTERS)

    if counters is None or not isinstance(counters, list) or len(counters) == 0:
        raise HomeAssistantError(
            f"{service_call.service}: Unrecognised response from API: {result}"
        )

    counter = counters[0]  # single counter for account

    message = counter.get(ATTR_MESSAGE)
    sent = counter.get(ATTR_SENT)
    if not sent:
        raise HomeAssistantError(
            f"{service_call.service}: Readings not sent: {message}"
        )

    return {ATTR_READINGS: value, ATTR_SENT: sent, ATTR_MESSAGE: message}


async def _async_handle_get_bill(
    hass: HomeAssistant, service_call: ServiceCall, coordinator: MyGasCoordinator
) -> dict[str, Any]:
    device_id = service_call.data.get(ATTR_DEVICE_ID)
    bill_date = service_call.data.get(ATTR_DATE, get_bill_date())
    email = service_call.data.get(ATTR_EMAIL)

    result = await coordinator.async_get_bill(device_id, bill_date, email)

    if result is None:
        raise HomeAssistantError(f"{service_call.service}: Empty response from API.")
    url = result.get(CONF_URL)
    if url is None and email is None:
        raise HomeAssistantError(
            f"{service_call.service}: Unrecognised response from API: {result}"
        )
    return {
        ATTR_DATE: bill_date,
        CONF_URL: unquote(url) if url else None,
        ATTR_EMAIL: unquote(email) if email else None,
    }


SERVICES: dict[str, ServiceDescription] = {
    SERVICE_REFRESH: ServiceDescription(
        SERVICE_REFRESH, _async_handle_refresh, SERVICE_REFRESH_SCHEMA
    ),
    SERVICE_SEND_READINGS: ServiceDescription(
        SERVICE_SEND_READINGS, _async_handle_send_readings, SERVICE_SEND_READINGS_SCHEMA
    ),
    SERVICE_GET_BILL: ServiceDescription(
        SERVICE_GET_BILL, _async_handle_get_bill, SERVICE_GET_BILL_SCHEMA
    ),
}


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the MyGas services."""

    @verify_domain_control(hass, DOMAIN)
    async def _async_handle_service(service_call: ServiceCall) -> None:
        """Call a service."""
        _LOGGER.debug("Service call %s", service_call.service)

        try:
            device_id = service_call.data.get(ATTR_DEVICE_ID)
            coordinator = await async_get_coordinator(hass, device_id)

            result = await SERVICES[service_call.service].service_func(
                hass, service_call, coordinator
            )

            hass.bus.async_fire(
                event_type=f"{DOMAIN}_{service_call.service}_completed",
                event_data={ATTR_DEVICE_ID: device_id, **result},
                context=service_call.context,
            )

            _LOGGER.debug(
                "Service call '%s' successfully finished", service_call.service
            )

        except Exception as exc:
            _LOGGER.error(
                "Service call '%s' failed. Error: %s", service_call.service, exc
            )

            hass.bus.async_fire(
                event_type=f"{DOMAIN}_{service_call.service}_failed",
                event_data={
                    ATTR_DEVICE_ID: service_call.data.get(ATTR_DEVICE_ID),
                    CONF_ERROR: str(exc),
                },
                context=service_call.context,
            )
            raise HomeAssistantError(
                f"Service call {service_call.service} failed. Error: {exc}"
            ) from exc

    for service in SERVICES.values():
        if hass.services.has_service(DOMAIN, service.name):
            continue
        hass.services.async_register(
            DOMAIN, service.name, _async_handle_service, service.schema
        )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload MyGas services."""

    if hass.data.get(DOMAIN):
        return

    for service in SERVICES:
        hass.services.async_remove(domain=DOMAIN, service=service)
