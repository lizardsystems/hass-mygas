"""Constants for the MyGas integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "mygas"

ATTRIBUTION: Final = "Данные получены от Мой Газ"
MANUFACTURER: Final = "Мой Газ"
ACCOUNT_MODEL: Final = "Лицевой счет"

API_TIMEOUT: Final = 30
API_MAX_TRIES: Final = 3
API_RETRY_DELAY: Final = 10
UPDATE_HOUR_BEGIN: Final = 1
UPDATE_HOUR_END: Final = 5

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]

REQUEST_REFRESH_DEFAULT_COOLDOWN = 5

CONF_ACCOUNT: Final = "account"
CONF_ACCOUNTS: Final = "accounts"
CONF_INFO: Final = "info"
CONF_AUTO_UPDATE: Final = "auto_update"

CONFIGURATION_URL: Final = "https://мойгаз.смородина.онлайн/"

FORMAT_DATE_SHORT_YEAR: Final = "%d.%m.%y"

ATTR_VALUE: Final = "value"
ATTR_STATUS: Final = "status"
ATTR_EMAIL: Final = "email"
ATTR_COUNTER: Final = "counter"
ATTR_MESSAGE: Final = "message"
ATTR_SENT: Final = "sent"
ATTR_READINGS: Final = "readings"
ATTR_BALANCE: Final = "balance"
SERVICE_REFRESH: Final = "refresh"
SERVICE_SEND_READINGS = "send_readings"
SERVICE_GET_BILL: Final = "get_bill"
ATTR_ELS = "els"
ATTR_IS_ELS = "is_els"
ATTR_LSPU_INFO_GROUP = "lspuInfoGroup"
ATTR_COUNTERS: Final = "counters"
ATTR_ALIAS: Final = "alias"
ATTR_LAST_UPDATE_TIME: Final = "last_update_time"
ATTR_JNT_ACCOUNT_NUM: Final = "jntAccountNum"
ATTR_UUID: Final = "uuid"
ATTR_SERIAL_NUM: Final = "serialNumber"
ATTR_ACCOUNT_ID: Final = "accountId"
