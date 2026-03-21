"""Wise (TransferWise) CSV format.

Wise exports: TransferWise ID, Date, Amount, Currency, Description,
Payment Reference, Running Balance, Exchange From, Exchange To, etc.
"""

COLUMNS = {
    "date": "Date",
    "amount": "Amount",
    "currency": "Currency",
    "payee": "Description",
    "reference": "Payment Reference",
    "balance": "Running Balance",
}

DATE_FORMAT = "%d-%m-%Y"

DEFAULT_ACCOUNT = "assets:bank:wise"
