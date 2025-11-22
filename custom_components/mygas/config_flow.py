"""Config flow for MyGas integration."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
from random import randrange
from typing import Any

import aiohttp
from aiomygas import MyGasApi, SimpleMyGasAuth
from aiomygas.exceptions import MyGasApiError, MyGasAuthError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_MAX_TRIES, API_RETRY_DELAY, API_TIMEOUT, DOMAIN
from .exceptions import CannotConnect, InvalidAuth

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect to MyGas."""
    try:
        session = async_get_clientsession(hass)
        auth = SimpleMyGasAuth(
            identifier=data[CONF_USERNAME],
            password=data[CONF_PASSWORD],
            session=session,
        )
        api = MyGasApi(auth)
        account = str(data[CONF_USERNAME]).lower()
        tries = 0
        api_timeout = API_TIMEOUT
        api_retry_delay = API_RETRY_DELAY
        _LOGGER.info("Connecting to MyGas account %s", account)
        while True:
            tries += 1
            try:
                async with asyncio.timeout(api_timeout):
                    _ = await api.async_get_accounts()
                return {"title": str(data[CONF_USERNAME]).lower()}

            except TimeoutError:
                api_timeout += API_TIMEOUT
                _LOGGER.debug("Timeout connecting to MyGas account %s", account)

            if tries >= API_MAX_TRIES:
                raise CannotConnect

            # Wait before attempting to connect again.
            _LOGGER.warning(
                "Failed to connect to MyGas. Try %d: Wait %d seconds and try again",
                tries,
                api_retry_delay,
            )
            await asyncio.sleep(api_retry_delay)
            api_retry_delay += API_RETRY_DELAY + randrange(API_RETRY_DELAY)

    except MyGasAuthError as exc:
        raise InvalidAuth from exc
    except (MyGasApiError, aiohttp.ClientError) as exc:
        raise CannotConnect from exc


class MyGasConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MyGas."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_USERNAME].lower()}")
            self._abort_if_unique_id_configured()
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Handle reconfiguration of an existing MyGas config entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_USERNAME].lower()}")
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data_updates=user_input,
            )
        reconf_entry = self._get_reconfigure_entry()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME, default=reconf_entry.data[CONF_USERNAME]
                    ): str,
                    vol.Required(
                        CONF_PASSWORD, default=reconf_entry.data[CONF_PASSWORD]
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthorization request from MyGas."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication with MyGas."""
        errors: dict[str, str] = {}
        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            user_input = {**reauth_entry.data, **user_input}
            try:
                await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(reauth_entry, data=user_input)

        return self.async_show_form(
            description_placeholders={CONF_USERNAME: reauth_entry.data[CONF_USERNAME]},
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )
