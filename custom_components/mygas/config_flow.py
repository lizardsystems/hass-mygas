"""Config flow for MyGas integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
from aiomygas import MyGasApi, SimpleMyGasAuth
from aiomygas.exceptions import MyGasApiError, MyGasAuthError
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .decorators import async_retry

_LOGGER = logging.getLogger(__name__)


@async_retry
async def _async_validate_credentials(
    hass: HomeAssistant, username: str, password: str
) -> dict[str, Any]:
    """Validate credentials by attempting login."""
    session = async_get_clientsession(hass)
    auth = SimpleMyGasAuth(
        identifier=username,
        password=password,
        session=session,
    )
    api = MyGasApi(auth)
    await api.async_get_accounts()
    return {"title": username.lower()}


class MyGasConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MyGas."""

    VERSION = 1

    async def _async_try_validate(
        self,
        username: str,
        password: str,
        errors: dict[str, str],
        context: str = "",
    ) -> dict[str, Any] | None:
        """Try to validate credentials and return result on success."""
        try:
            result = await _async_validate_credentials(
                self.hass, username, password
            )
            _LOGGER.debug("Credentials validated for %s", username)
            return result
        except MyGasAuthError as err:
            _LOGGER.warning(
                "Invalid credentials for %s: %s", username, err, exc_info=True
            )
            errors["base"] = "invalid_auth"
        except (MyGasApiError, aiohttp.ClientError) as err:
            _LOGGER.warning(
                "Connection error for %s: %s", username, err, exc_info=True
            )
            errors["base"] = "cannot_connect"
        except Exception:
            _LOGGER.exception(
                "Unexpected exception%s", f" during {context}" if context else ""
            )
            errors["base"] = "unknown"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip().lower()
            password = user_input[CONF_PASSWORD]

            if await self._async_try_validate(username, password, errors):
                await self.async_set_unique_id(username)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=username,
                    data={CONF_USERNAME: username, CONF_PASSWORD: password},
                )

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

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing MyGas config entry."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip().lower()
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(username)
            self._abort_if_unique_id_mismatch()

            if await self._async_try_validate(
                username, password, errors, context="reconfigure"
            ):
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=reconfigure_entry.data[CONF_USERNAME],
                    ): str,
                    vol.Required(
                        CONF_PASSWORD,
                        default=reconfigure_entry.data[CONF_PASSWORD],
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
        reauth_entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            username = reauth_entry.data[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            if await self._async_try_validate(
                username, password, errors, context="reauth"
            ):
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: password},
                )

        return self.async_show_form(
            description_placeholders={
                CONF_USERNAME: reauth_entry.data[CONF_USERNAME],
            },
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> MyGasOptionsFlowHandler:
        """Get the options flow handler."""
        return MyGasOptionsFlowHandler()


OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=168)
        ),
    }
)


class MyGasOptionsFlowHandler(OptionsFlowWithReload):
    """Handle MyGas options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA,
                {
                    CONF_SCAN_INTERVAL: self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                },
            ),
        )
