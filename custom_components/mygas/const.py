"""Constants for the MyGas integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "mygas"

ATTRIBUTION: Final = "Данные получены от Мой Газ"
MANUFACTURER: Final = "Мой Газ"
ACCOUNT_MODEL: Final = "Лицевой счет"
SERVICE_MODEL: Final = "Услуга"

API_TIMEOUT: Final = 30
API_MAX_TRIES: Final = 3
API_RETRY_DELAY: Final = 10

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]

REQUEST_REFRESH_DEFAULT_COOLDOWN = 5

CONF_ACCOUNT: Final = "account"
CONF_ACCOUNTS: Final = "accounts"
CONF_INFO: Final = "info"
CONF_SCAN_INTERVAL: Final = "scan_interval"
DEFAULT_SCAN_INTERVAL: Final = 24

# Punycode (IDNA) encoding of "https://мойгаз.смородина.онлайн/".
# The raw Cyrillic host fails to parse in Home Assistant on Python 3.14
# (yarl/idna), so the device configuration_url is stored pre-encoded.
CONFIGURATION_URL: Final = "https://xn--80afnfom.xn--80ahmohdapg.xn--80asehdb/"

ATTR_VALUE: Final = "value"
ATTR_EMAIL: Final = "email"
ATTR_COUNTER: Final = "counter"
ATTR_MESSAGE: Final = "message"
ATTR_SENT: Final = "sent"
ATTR_READINGS: Final = "readings"
SERVICE_REFRESH: Final = "refresh"
SERVICE_SEND_READINGS: Final = "send_readings"
SERVICE_GET_BILL: Final = "get_bill"
ATTR_ELS: Final = "els"
ATTR_IS_ELS: Final = "is_els"
ATTR_LSPU_INFO_GROUP: Final = "lspuInfoGroup"
ATTR_COUNTERS: Final = "counters"
ATTR_SERVICES: Final = "services"
ATTR_ALIAS: Final = "alias"
ATTR_LAST_UPDATE_TIME: Final = "last_update_time"
ATTR_JNT_ACCOUNT_NUM: Final = "jntAccountNum"
ATTR_UUID: Final = "uuid"
ATTR_SERIAL_NUM: Final = "serialNumber"
ATTR_ACCOUNT_ID: Final = "accountId"
