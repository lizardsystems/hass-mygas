"""Config flow for MyGas integration."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from random import randrange
from typing import Any

import aiohttp
import voluptuous as vol
from aiomygas import MyGasApi, SimpleMyGasAuth
from aiomygas.exceptions import MyGasApiError, MyGasAuthError
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlowWithConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_MAX_TRIES, API_RETRY_DELAY, API_TIMEOUT, CONF_AUTO_UPDATE, DOMAIN
from .exceptions import CannotConnect, InvalidAuth

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
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


class MyGasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MyGas."""

    VERSION = 1
    reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle reauthorization request from MyGas."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm re-authentication with MyGas."""
        errors: dict[str, str] = {}

        if user_input:
            assert self.reauth_entry is not None
            password = user_input[CONF_PASSWORD]
            data = {
                CONF_USERNAME: self.reauth_entry.data[CONF_USERNAME],
                CONF_PASSWORD: password,
            }

            try:
                await validate_input(self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self.reauth_entry,
                    data={
                        **self.reauth_entry.data,
                        CONF_PASSWORD: password,
                    },
                )
                await self.hass.config_entries.async_reload(self.reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return MyGasOptionsFlowHandler(config_entry)


class MyGasOptionsFlowHandler(OptionsFlowWithConfigEntry):
    """Handle an options flow for MyGas."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }

            try:
                await validate_input(self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                changed = self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    options=user_input,
                )
                if changed:
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                return self.async_create_entry(data=user_input)

        default_username = self.config_entry.data[CONF_USERNAME]
        default_password = self.config_entry.data[CONF_PASSWORD]
        default_auto_update = self.config_entry.options.get(CONF_AUTO_UPDATE, False)
        options_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=default_username): str,
                vol.Required(CONF_PASSWORD, default=default_password): str,
                vol.Optional(
                    CONF_AUTO_UPDATE,
                    default=default_auto_update,
                ): bool,
            }
        )

        data_schema = self.add_suggested_values_to_schema(
            options_schema,
            user_input or self.options,
        )
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=data_schema,
        )
