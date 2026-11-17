from __future__ import annotations

import re
from dataclasses import asdict, dataclass

FIELD_LABELS = {
    "invoice_number": "Invoice",
    "vendor": "Vendor",
    "date": "Date",
    "currency": "Currency",
    "subtotal": "Subtotal",
    "tax": "Tax",
    "total": "Total",
}


@dataclass(frozen=True)
class RawInvoiceFields:
    
    invoice_number: str | None = None
    vendor: str | None = None
    date: str | None = None
    currency: str | None = None
    subtotal: str | None = None
    tax: str | None = None
    total: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)


def _label_pattern(label: str) -> re.Pattern[str]:
    
    return re.compile(rf"^[ \t]*{re.escape(label)}[ \t]*:[ \t]*(?P<value>.*)$", re.I | re.M)


_PATTERNS = {field: _label_pattern(label) for field, label in FIELD_LABELS.items()}


def parse_fields(text: str) -> RawInvoiceFields:
   
    found: dict[str, str | None] = {}
    for field, pattern in _PATTERNS.items():
        match = pattern.search(text)
        value = match.group("value").strip() if match else ""
        found[field] = value or None
    return RawInvoiceFields(**found)
