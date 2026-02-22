"""MyGas Account Coordinator."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from aiomygas import MyGasApi, SimpleMyGasAuth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
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
    ATTR_SERVICES,
    ATTR_UUID,
    CONF_ACCOUNT,
    CONF_ACCOUNTS,
    CONF_INFO,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    REQUEST_REFRESH_DEFAULT_COOLDOWN,
)
from .decorators import async_api_request_handler
from .helpers import make_account_device_id, make_device_id

_LOGGER = logging.getLogger(__name__)


class MyGasCoordinator(DataUpdateCoordinator):
    """Coordinator is responsible for querying the device at a specified route."""

    config_entry: ConfigEntry
    _api: MyGasApi

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialise a custom coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=REQUEST_REFRESH_DEFAULT_COOLDOWN,
                immediate=False,
            ),
        )
        self.force_next_update = False
        self.data = {}
        session = async_get_clientsession(hass)
        self.username = config_entry.data[CONF_USERNAME]
        self.password = config_entry.data[CONF_PASSWORD]
        scan_interval_hours: int = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        self.update_interval = timedelta(hours=scan_interval_hours)
        auth = SimpleMyGasAuth(self.username, self.password, session)
        self._api = MyGasApi(auth)

    async def async_force_refresh(self) -> None:
        """Force refresh data."""
        self.force_next_update = True
        await self.async_refresh()

    async def _async_update_data(self) -> dict[str, Any] | None:
        """Fetch data from MyGas."""
        _data: dict[str, Any] = self.data if self.data is not None else {}
        new_data: dict[str, Any] = {
            ATTR_LAST_UPDATE_TIME: dt_util.now(),
        }
        _LOGGER.debug("Start updating data...")
        try:
            accounts_info = _data.get(CONF_ACCOUNTS)
            if accounts_info is None or self.force_next_update:
                # get account general information
                _LOGGER.debug("Get accounts info for %s", self.username)
                accounts_info = await self._async_get_accounts()
                if accounts_info:
                    _LOGGER.debug(
                        "Accounts info for %s retrieved successfully", self.username
                    )
                else:
                    _LOGGER.warning(
                        "Accounts info for %s not retrieved", self.username
                    )
                    return new_data
            else:
                _LOGGER.debug(
                    "Accounts info for %s retrieved from cache", self.username
                )

            new_data[CONF_ACCOUNTS] = accounts_info

            if accounts_info.get("elsGroup"):
                _LOGGER.debug(
                    "Accounts info for els accounts %s retrieved successfully",
                    self.username,
                )
                new_data[ATTR_IS_ELS] = True
                new_data[CONF_INFO] = await self.retrieve_els_accounts_info(
                    accounts_info
                )
            elif accounts_info.get("lspu"):
                _LOGGER.debug(
                    "Accounts info for lspu accounts %s retrieved successfully",
                    self.username,
                )

                new_data[ATTR_IS_ELS] = False
                new_data[CONF_INFO] = await self.retrieve_lspu_accounts_info(
                    accounts_info
                )
            else:
                _LOGGER.warning(
                    "Account %s does not have els or lspu in accounts info",
                    self.username,
                )
                return None

        except ConfigEntryAuthFailed:
            raise
        except Exception as exc:  # pylint: disable=broad-except
            raise UpdateFailed(f"Error communicating with API: {exc}") from exc
        else:
            _LOGGER.debug("Data updated successfully for %s", self.username)
            _LOGGER.debug("%s", new_data)

            return new_data
        finally:
            self.force_next_update = False
            scan_interval_hours: int = self.config_entry.options.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
            )
            self.update_interval = timedelta(hours=scan_interval_hours)
            _LOGGER.debug(
                "Update interval: %s hours", scan_interval_hours
            )

    async def retrieve_els_accounts_info(
        self, accounts_info: dict[str, Any]
    ) -> dict[int, Any]:
        """Retrieve ELS accounts info."""
        els_list = accounts_info.get("elsGroup")
        els_info = {}
        for els in els_list:
            els_id = els.get("els", {}).get("id")
            if not els_id:
                _LOGGER.warning("id not found in els info")
                continue
            els_id = int(els_id)
            _LOGGER.debug("Get els info for %d", els_id)
            els_item_info = await self._async_get_els_info(els_id)
            if els_item_info:
                els_info[els_id] = els_item_info
                _LOGGER.debug("Els info for id=%d retrieved successfully", els_id)
            else:
                _LOGGER.warning("Els info for id=%d not retrieved", els_id)
        return els_info

    async def retrieve_lspu_accounts_info(
        self, accounts_info: dict[str, Any]
    ) -> dict[int, Any]:
        """Retrieve LSPU accounts info."""
        lspu_list = accounts_info.get("lspu")
        lspu_info = {}
        for lspu in lspu_list:
            lspu_id = lspu.get("id")
            if not lspu_id:
                _LOGGER.warning("id not found in lspu info")
                continue

            lspu_id = int(lspu_id)
            _LOGGER.debug("Get lspu info for %s", lspu_id)
            lspu_item_info = await self._async_get_lspu_info(lspu_id)
            if lspu_item_info:
                if isinstance(lspu_item_info, list):
                    lspu_info[lspu_id] = lspu_item_info
                else:
                    lspu_info[lspu_id] = [lspu_item_info]
                _LOGGER.debug("Lspu info for %s retrieved successfully", lspu_id)
            else:
                _LOGGER.warning("Lspu info for %s not retrieved", lspu_id)
        return lspu_info

    def get_accounts(self) -> dict[int, dict[str | int, Any]]:
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

    def get_lspu_accounts(self, account_id: int) -> list[dict[str | int, Any]]:
        """Get LSPU accounts."""
        _data = self.get_accounts()[account_id]
        if self.is_els():
            _lspu_accounts = _data[ATTR_LSPU_INFO_GROUP]
        else:
            _lspu_accounts = _data if isinstance(_data, list) else [_data]
        return _lspu_accounts

    def get_counters(
        self, account_id: int, lspu_account_id: int
    ) -> list[dict[str, Any]]:
        """Get counter data."""
        _accounts = self.get_lspu_accounts(account_id)[lspu_account_id]
        return _accounts.get(ATTR_COUNTERS, [])

    def get_services(
        self, account_id: int, lspu_account_id: int
    ) -> list[dict[str, Any]]:
        """Get services."""
        account = self.get_lspu_accounts(account_id)[lspu_account_id]
        return account.get(ATTR_SERVICES, [])

    async def find_account_by_device_id(
        self, device_id: str
    ) -> tuple[int | None, int | None, int | None]:
        """Find device by id."""
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get(device_id)
        if not device:
            raise HomeAssistantError(f"Device {device_id} not found")

        for account_id in self.get_accounts():
            for lspu_account_id in range(len(self.get_lspu_accounts(account_id))):
                _account_number = self.get_account_number(
                    account_id, lspu_account_id
                )
                # Check account-level device
                if device.identifiers == {
                    (DOMAIN, make_account_device_id(_account_number))
                }:
                    return account_id, lspu_account_id, None
                # Check counter-level device
                counters = self.get_counters(account_id, lspu_account_id)
                for counter_id, counter in enumerate(counters):
                    _counter_uuid = counter.get(ATTR_UUID)
                    if not _counter_uuid:
                        continue
                    if device.identifiers == {
                        (DOMAIN, make_device_id(_account_number, _counter_uuid))
                    }:
                        return account_id, lspu_account_id, counter_id
        return None, None, None

    @async_api_request_handler
    async def _async_get_client_info(self) -> dict[str, Any]:
        """Fetch client info."""
        return await self._api.async_get_client_info()

    @async_api_request_handler
    async def _async_get_accounts(self) -> dict[str, Any]:
        """Fetch accounts info."""
        return await self._api.async_get_accounts()

    @async_api_request_handler
    async def _async_get_els_info(self, els_id: int) -> dict[str, Any]:
        """Fetch els info."""
        return await self._api.async_get_els_info(els_id)

    @async_api_request_handler
    async def _async_get_lspu_info(self, lspu_id: int) -> dict[str, Any]:
        """Fetch lspu info."""
        return await self._api.async_get_lspu_info(lspu_id)

    @async_api_request_handler
    async def _async_get_charges(self, lspu_id: int) -> dict[str, Any]:
        """Fetch charges info."""
        return await self._api.async_get_charges(lspu_id)

    @async_api_request_handler
    async def _async_get_payments(self, lspu_id: int) -> dict[str, Any]:
        """Fetch payments info."""
        return await self._api.async_get_payments(lspu_id)

    @async_api_request_handler
    async def _async_send_readings(
        self,
        lspu_id: int,
        equipment_uuid: str,
        value: float,
        els_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Send readings with handle errors by decorator."""
        return await self._api.async_indication_send(
            lspu_id, equipment_uuid, value, els_id
        )

    @async_api_request_handler
    async def _async_get_receipt(
        self, date_iso_short: str, email: str | None, account_number: int, is_els: bool
    ) -> dict[str, Any]:
        """Get receipt data."""
        return await self._api.async_get_receipt(
            date_iso_short,
            email,  # pyright: ignore[reportArgumentType]
            account_number,
            is_els,
        )

    async def async_get_bill(
        self,
        device_id: str,
        bill_date: date | None = None,
        email: str | None = None,
    ) -> dict[str, Any] | None:
        """Get receipt data."""
        if bill_date is None:
            bill_date = dt_util.now().date()
        date_iso_short = bill_date.strftime("%Y-%m-%d")
        account_id, *_ = await self.find_account_by_device_id(device_id)
        if account_id is not None:
            is_els = self.is_els()
            return await self._async_get_receipt(
                date_iso_short, email, account_id, is_els
            )
        return None

    async def async_send_readings(
        self,
        device_id: str,
        value: float,
    ) -> list[dict[str, Any]]:
        """Send readings with handle errors by decorator."""
        account_id, lspu_account_id, counter_id = (
            await self.find_account_by_device_id(device_id)
        )
        if account_id is None or lspu_account_id is None or counter_id is None:
            raise HomeAssistantError(
                f"Account not found for device {device_id}"
            )
        lspu_accounts = self.get_lspu_accounts(account_id)
        if not lspu_accounts:
            raise HomeAssistantError(
                f"No LSPU accounts found for account {account_id}"
            )
        lspu_account = lspu_accounts[lspu_account_id]
        if not lspu_account:
            raise HomeAssistantError(
                f"LSPU account {lspu_account_id} not found"
            )
        lspu_id = lspu_account[ATTR_ACCOUNT_ID]

        if self.is_els():
            els_id = account_id
        else:
            els_id = None
        counters = self.get_counters(account_id, lspu_account_id)
        if not counters:
            raise HomeAssistantError(
                f"No counters found for account {account_id}"
            )
        equipment_uuid = counters[counter_id][ATTR_UUID]
        if not equipment_uuid:
            raise HomeAssistantError(
                f"Counter UUID not found for counter {counter_id}"
            )
        return await self._async_send_readings(
            lspu_id,
            equipment_uuid,
            value,
            els_id,
        )
