"""Constants for the MyGas integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "mygas"

ATTRIBUTION: Final = "Данные получены от Мой Газ"
MANUFACTURER: Final = "Мой Газ"
MODEL: Final = "MyGas"

API_TIMEOUT: Final = 30
API_MAX_TRIES: Final = 3
API_RETRY_DELAY: Final = 10
UPDATE_HOUR_BEGIN: Final = 1
UPDATE_HOUR_END: Final = 5
UPDATE_INTERVAL: Final[timedelta] = timedelta(days=1)

REQUEST_REFRESH_DEFAULT_COOLDOWN = 5

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

CONF_ACCOUNT: Final = "account"
CONF_DATA: Final = "data"
CONF_LINK: Final = "link"
CONF_ACCOUNTS: Final = "accounts"
CONF_RESULT: Final = "result"
CONF_INFO: Final = "info"
CONF_PAYMENT: Final = "payment"
CONF_READINGS: Final = "readings"
CONF_AUTO_UPDATE: Final = "auto_update"

CONFIGURATION_URL: Final = "https://мойгаз.смородина.онлайн/"

FORMAT_DATE_SHORT_YEAR: Final = "%d.%m.%y"
FORMAT_DATE_FULL_YEAR: Final = "%d.%m.%Y"

ATTR_LABEL: Final = "Label"

REFRESH_TIMEOUT = timedelta(minutes=10)
ATTR_VALUE: Final = "value"
ATTR_STATUS: Final = "status"
ATTR_EMAIL: Final = "email"
ATTR_COUNTER: Final = "counter"
ATTR_MESSAGE: Final = "message"
ATTR_SENT: Final = "sent"
ATTR_COORDINATOR: Final = "coordinator"
ATTR_READINGS: Final = "readings"
ATTR_BALANCE: Final = "balance"
SERVICE_REFRESH: Final = "refresh"
SERVICE_SEND_READINGS = "send_readings"
SERVICE_GET_BILL: Final = "get_bill"
ACTION_TYPE_SEND_READINGS: Final = "send_readings"
ACTION_TYPE_BILL: Final = "get_bill"
ACTION_TYPE_REFRESH: Final = "refresh"
ATTR_LSPU_INFO: Final = "lspu_info"
ATTR_ELS_INFO: Final = "els_info"
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
