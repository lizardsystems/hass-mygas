"""Constants for MyGas tests."""
from __future__ import annotations

MOCK_USERNAME = "test@example.com"
MOCK_PASSWORD = "testpassword"

# LSPU account response from async_get_accounts
MOCK_ACCOUNTS_RESPONSE = {
    "lspu": [
        {
            "id": 12345,
            "name": "Иванов Иван Иванович",
        }
    ]
}

# LSPU info response from async_get_lspu_info
MOCK_LSPU_INFO_RESPONSE = {
    "account": "1234567890",
    "alias": "Дом",
    "accountId": 12345,
    "balance": 150.50,
    "parameters": [
        {"name": "Адрес", "value": "г. Москва, ул. Примерная, д. 1"},
    ],
    "balances": [
        {
            "uuid": "bal-001",
            "date": "2026-01-31",
            "name": "Январь 2026",
            "chargedSum": 850.00,
            "paidSum": 750.00,
            "debtSum": 100.00,
            "balanceStartSum": 0.00,
            "balanceEndSum": 100.00,
            "chargedVolume": 95.5,
            "circulationSum": 850.00,
            "forgivenDebt": 0.00,
            "plannedSum": 900.00,
            "privilegeSum": 0.00,
            "privilegeVolume": 0.0,
            "restoredDebt": 0.00,
            "paymentAdjustments": 0.00,
            "endBalanceApgp": 0.00,
            "prepaymentChargedAccumSum": 0.00,
        }
    ],
    "services": [
        {
            "id": "02",
            "name": "Газоснабжение природным газом",
            "balance": "-6.32",
            "providerName": 'ООО "Газпром межрегионгаз"',
            "children": [
                {
                    "name": "Плита и колонка(+От)",
                    "norm": 29.52,
                    "price": 9.014,
                    "tariff": 266.09328,
                    "equipmentUuid": "abc-def-123",
                    "startDate": "2017-10-09T00:00:00",
                },
                {
                    "name": "Отопление",
                    "norm": 12.4,
                    "price": 9.014,
                    "tariff": 111.7736,
                    "equipmentUuid": None,
                    "startDate": "2020-01-01T00:00:00",
                },
            ],
        },
        {
            "id": "04",
            "name": "Пеня за газ",
            "balance": "-3.69",
            "providerName": 'ООО "Газпром межрегионгаз"',
            "children": [],
        },
        {
            "id": "61",
            "name": "Техническое обслуживание",
            "balance": "0",
            "providerName": 'ООО "Газпром межрегионгаз"',
            "children": [],
        },
    ],
    "counters": [
        {
            "uuid": "abc-def-123",
            "name": "Счетчик газа",
            "model": "BK-G4",
            "serialNumber": "SN12345",
            "state": "Активный",
            "equipmentKind": "Газовый счетчик",
            "position": "Кухня",
            "serviceName": "Газоснабжение",
            "numberOfRates": 1,
            "averageRate": 12.5,
            "checkDate": "2030-01-01T00:00:00",
            "techSupportDate": "2030-06-01T00:00:00",
            "sealDate": "2020-01-01T00:00:00",
            "factorySealDate": "2019-06-01T00:00:00",
            "commissionedOn": "2019-01-01T00:00:00",
            "price": {"day": 8.50},
            "values": [
                {
                    "date": "2026-01-15T00:00:00",
                    "valueDay": 1250.5,
                    "rate": 15.3,
                }
            ],
        }
    ],
}

# Send readings response
MOCK_SEND_READINGS_RESPONSE = [
    {
        "counters": [
            {
                "message": "Показания приняты",
                "sent": True,
            }
        ]
    }
]

# Receipt response
MOCK_RECEIPT_RESPONSE = {
    "url": "https://example.com/receipt.pdf",
}
