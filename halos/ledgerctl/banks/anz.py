"""ANZ New Zealand CSV format.

ANZ exports: Type, Details, Particulars, Code, Reference, Amount, Date, ForeignCurrencyAmount, ConversionCharge
The payee info is typically in Details/Particulars.
"""

COLUMNS = {
    "date": "Date",
    "amount": "Amount",
    "payee": "Details",
    "particulars": "Particulars",
    "code": "Code",
    "reference": "Reference",
}

DATE_FORMAT = "%d/%m/%Y"

DEFAULT_ACCOUNT = "assets:bank:anz:checking"
