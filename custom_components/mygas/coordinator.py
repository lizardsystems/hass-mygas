"""MyGas Account Coordinator."""
from __future__ import annotations

import logging
from datetime import date
from random import randrange
from typing import Any

from aiomygas import MyGasApi, SimpleMyGasAuth
from aiomygas.exceptions import MyGasAuthError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ACCOUNT_ID,
    ATTR_ALIAS,
    ATTR_COUNTERS,
    ATTR_ELS,
    ATTR_IS_ELS,
    ATTR_JNT_ACCOUNT_NUM,
    ATTR_LAST_UPDATE_TIME,
    ATTR_LSPU_INFO_GROUP,
    ATTR_UUID,
    CONF_ACCOUNT,
    CONF_ACCOUNTS,
    CONF_INFO,
    DOMAIN,
    REQUEST_REFRESH_DEFAULT_COOLDOWN,
    UPDATE_HOUR_BEGIN,
    UPDATE_HOUR_END,
    CONF_AUTO_UPDATE,
)
from .decorators import async_api_request_handler
from .helpers import make_device_id, get_update_interval


class MyGasCoordinator(DataUpdateCoordinator):
    """Coordinator is responsible for querying the device at a specified route."""

    _api: MyGasApi
    data: dict[str, Any]
    username: str
    password: str
    force_next_update: bool
    auto_update: bool

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        *,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialise a custom coordinator."""
        super().__init__(
            hass,
            logger,
            name=DOMAIN,
            request_refresh_debouncer=Debouncer(
                hass,
                logger,
                cooldown=REQUEST_REFRESH_DEFAULT_COOLDOWN,
                immediate=False,
            ),
        )
        self.force_next_update = False
        self.data = {}
        session = async_get_clientsession(hass)
        self.username = config_entry.data[CONF_USERNAME]
        self.password = config_entry.data[CONF_PASSWORD]
        self.auto_update = config_entry.data.get(CONF_AUTO_UPDATE, False)
        auth = SimpleMyGasAuth(self.username, self.password, session)
        self._api = MyGasApi(auth)

    async def async_force_refresh(self):
        """Force refresh data."""
        self.force_next_update = True
        await self.async_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from MyGas."""
        _data: dict[str, Any] = self.data if self.data is not None else {}
        new_data: dict[str, Any] = {
            ATTR_LAST_UPDATE_TIME: dt_util.now(),
        }
        self.logger.debug("Start updating data...")
        try:
            accounts_info = _data.get(CONF_ACCOUNTS)
            if accounts_info is None or self.force_next_update:
                # get account general information
                self.logger.debug("Get accounts info for %s", self.username)
                accounts_info = await self._async_get_accounts()
                if accounts_info:
                    self.logger.debug(
                        "Accounts info for %s retrieved successfully", self.username
                    )
                else:
                    self.logger.warning(
                        "Accounts info for %s not retrieved", self.username
                    )
                    return new_data
            else:
                self.logger.debug(
                    "Accounts info for %s retrieved from cache", self.username
                )

            new_data[CONF_ACCOUNTS] = accounts_info

            if accounts_info.get("elsGroup"):
                self.logger.debug(
                    "Accounts info for els accounts %s retrieved successfully",
                    self.username,
                )
                new_data[ATTR_IS_ELS] = True
                new_data[CONF_INFO] = await self.retrieve_els_accounts_info(
                    accounts_info
                )
            elif accounts_info.get("lspu"):
                self.logger.debug(
                    "Accounts info for lspu accounts %s retrieved successfully",
                    self.username,
                )

                new_data[ATTR_IS_ELS] = False
                new_data[CONF_INFO] = await self.retrieve_lspu_accounts_info(
                    accounts_info
                )
            else:
                self.logger.warning(
                    "Account %s does not have els or lspu in accounts info",
                    self.username,
                )
                return new_data

            self.logger.debug("Data updated successfully for %s", self.username)
            self.logger.debug("%s", new_data)

            return new_data

        except MyGasAuthError as exc:
            raise ConfigEntryAuthFailed("Incorrect Login or Password") from exc
        except Exception as exc:  # pylint: disable=broad-except
            raise UpdateFailed(f"Error communicating with API: {exc}") from exc
        finally:
            self.force_next_update = False
            if self.auto_update:
                self.update_interval = get_update_interval(
                    randrange(UPDATE_HOUR_BEGIN, UPDATE_HOUR_END),
                    randrange(60),
                    randrange(60),
                )
                self.logger.debug(
                    "Update interval: %s seconds", self.update_interval.total_seconds()
                )
            else:
                self.update_interval = None

    async def retrieve_els_accounts_info(self, accounts_info):
        """Retrieve ELS accounts info."""
        els_list = accounts_info.get("elsGroup")
        els_info = {}
        for els in els_list:
            els_id = els.get("els", {}).get("id")
            if not els_id:
                self.logger.warning("id not found in els info")
                continue
            els_id = int(els_id)
            self.logger.debug("Get els info for %d", els_id)
            els_item_info = await self._async_get_els_info(els_id)
            if els_item_info:
                els_info[els_id] = els_item_info
                self.logger.debug("Els info for id=%d retrieved successfully", els_id)
            else:
                self.logger.warning("Els info for id=%d not retrieved", els_id)
        return els_info

    async def retrieve_lspu_accounts_info(self, accounts_info):
        """Retrieve LSPU accounts info."""
        lspu_list = accounts_info.get("lspu")
        lspu_info = {}
        for lspu in lspu_list:
            lspu_id = lspu.get("id")
            if not lspu_id:
                self.logger.warning("id not found in lspu info")
                continue

            lspu_id = int(lspu_id)
            self.logger.debug("Get lspu info for %s", lspu_id)
            lspu_item_info = await self._async_get_lspu_info(lspu_id)
            if lspu_item_info:
                if lspu_item_info is list:
                    lspu_info[lspu_id] = lspu_item_info
                else:
                    lspu_info[lspu_id] = [lspu_item_info]
                self.logger.debug("Lspu info for %s retrieved successfully", lspu_id)
            else:
                self.logger.warning("Lspu info for %s not retrieved", lspu_id)
        return lspu_info

    def get_accounts(self) -> dict[int, dict[str, Any]]:
        """Get accounts info."""
        return self.data.get(CONF_INFO, {})

    def get_account_number(self, account_id: int, lspu_account_id: int) -> str:
        """Get account number."""
        account = self.get_accounts()[account_id]
        if self.is_els():
            _account_number = account.get(ATTR_ELS, {}).get(ATTR_JNT_ACCOUNT_NUM)
        else:
            _account_number = account[lspu_account_id].get(CONF_ACCOUNT)
        return _account_number

    def get_account_alias(self, account_id: int, lspu_account_id: int) -> str | None:
        """Get account alias."""
        account = self.get_accounts()[account_id]
        if self.is_els():
            _account_alias = account.get(ATTR_ELS, {}).get(ATTR_ALIAS)
        else:
            _account_alias = account[lspu_account_id].get(ATTR_ALIAS)
        return _account_alias

    def is_els(self) -> bool:
        """Account is ELS."""
        return self.data.get(ATTR_IS_ELS, False)

    def get_lspu_accounts(self, account_id: int) -> list[dict[str, Any]]:
        """Get LSPU accounts."""
        _data = self.get_accounts()[account_id]
        if self.is_els():
            _lspu_accounts = _data[ATTR_LSPU_INFO_GROUP]
        else:
            _lspu_accounts = _data
        return _lspu_accounts

    def get_counters(
        self, account_id: int, lspu_acount_id: int
    ) -> list[dict[str, Any]]:
        """Get counter data."""
        _accounts = self.get_lspu_accounts(account_id)[lspu_acount_id]
        return _accounts.get(ATTR_COUNTERS, [])

    async def find_account_by_device_id(
        self, device_id: str
    ) -> tuple[int | None, int | None, int | None] | None:
        """Find device by id."""
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get(device_id)

        for account_id in self.get_accounts():
            for lspu_account_id in range(len(self.get_lspu_accounts(account_id))):
                for counter_id in range(
                    len(self.get_counters(account_id, lspu_account_id))
                ):
                    _account_number = self.get_account_number(
                        account_id, lspu_account_id
                    )
                    _counter_uuid = self.get_counters(account_id, lspu_account_id)[
                        counter_id
                    ].get(ATTR_UUID)

                    if device.identifiers == {
                        (DOMAIN, make_device_id(_account_number, _counter_uuid))
                    }:
                        return account_id, lspu_account_id, counter_id
        return None, None, None

    @async_api_request_handler
    async def _async_get_client_info(self) -> dict[str, Any]:
        """Fetch client info."""
        _data = await self._api.async_get_client_info()
        return _data

    @async_api_request_handler
    async def _async_get_accounts(self) -> dict[str, Any]:
        """Fetch accounts info."""
        _data = await self._api.async_get_accounts()
        return _data

    @async_api_request_handler
    async def _async_get_els_info(self, els_id: int) -> dict[str, Any]:
        """Fetch els info."""
        _data = await self._api.async_get_els_info(els_id)
        return _data

    @async_api_request_handler
    async def _async_get_lspu_info(self, lspu_id: int) -> dict[str, Any]:
        """Fetch lspu info."""
        _data = await self._api.async_get_lspu_info(lspu_id)
        return _data

    @async_api_request_handler
    async def _async_get_charges(self, lspu_id: int) -> dict[str, Any]:
        """Fetch charges info."""
        _data = await self._api.async_get_charges(lspu_id)
        return _data

    @async_api_request_handler
    async def _async_get_payments(self, lspu_id: int) -> dict[str, Any]:
        """Fetch payments info."""
        _data = await self._api.async_get_payments(lspu_id)
        return _data

    @async_api_request_handler
    async def _async_send_readings(
        self,
        lspu_id: int,
        equipment_uuid: str,
        value: int | float,
        els_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Send readings with handle errors by decorator."""
        _data = await self._api.async_indication_send(
            lspu_id, equipment_uuid, value, els_id
        )
        return _data

    @async_api_request_handler
    async def _async_get_receipt(
        self, date_iso_short: str, email: str, account_number: int, is_els: bool
    ) -> dict[str, Any]:
        """Get receipt data."""
        _data = await self._api.async_get_receipt(
            date_iso_short, email, account_number, is_els
        )
        return _data

    async def async_get_bill(
        self,
        device_id: str,
        bill_date: date | None = None,
        email: str | None = None,
    ) -> dict[str, Any] | None:
        """Get receipt data."""
        date_iso_short = bill_date.strftime("%Y-%m-%d")
        account_id, *_ = await self.find_account_by_device_id(device_id)
        if account_id is not None:
            is_els = self.is_els()
            _data = await self._async_get_receipt(
                date_iso_short, email, account_id, is_els
            )
            return _data
        return None

    async def async_send_readings(
        self,
        device_id,
        value: int | float,
    ) -> list[dict[str, Any]]:
        """Send readings with handle errors by decorator."""

        account_id, lspu_account_id, counter_id = await self.find_account_by_device_id(
            device_id
        )

        lspu_id = self.get_lspu_accounts(account_id)[lspu_account_id].get(
            ATTR_ACCOUNT_ID
        )

        if self.is_els():
            els_id = account_id
        else:
            els_id = None

        equipment_uuid = self.get_counters(account_id, lspu_account_id)[counter_id].get(
            ATTR_UUID
        )

        _data = await self._async_send_readings(
            lspu_id,
            equipment_uuid,
            value,
            els_id,
        )
        return _data
