from __future__ import annotations
import re
from datetime import date, datetime
from decimal import Decimal


class NormalizationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


_MONEY_PATTERN = re.compile(r"^(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?$")

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y")


def parse_money_to_paise(raw: str) -> int:
    
    value = raw.strip()
    if not _MONEY_PATTERN.match(value):
        raise NormalizationError("invalid_amount", f"cannot read amount: {raw!r}")

    rupees = Decimal(value.replace(",", ""))
    return int((rupees * 100).to_integral_exact())


def parse_date(raw: str) -> date:
    value = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise NormalizationError("invalid_date", f"cannot read date: {raw!r}")


def normalize_vendor(raw: str) -> str:
    return " ".join(raw.split()).casefold()


def normalize_invoice_number(raw: str) -> str:
    return raw.strip().upper()
