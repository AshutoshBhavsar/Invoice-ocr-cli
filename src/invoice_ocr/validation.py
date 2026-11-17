from __future__ import annotations
import re
from dataclasses import dataclass, field
from datetime import date

from .normalize import (
    NormalizationError,
    normalize_invoice_number,
    normalize_vendor,
    parse_date,
    parse_money_to_paise,
)

from .parser import FIELD_LABELS, RawInvoiceFields

VALID = "valid"
NEEDS_REVIEW = "needs_review"

_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class ReviewReason:
    code: str  
    field: str | None  
    message: str 


@dataclass(frozen=True)
class NormalizedInvoice:
    """Clean values. A field is ``None`` if it was missing or unreadable."""

    invoice_number: str | None = None
    vendor: str | None = None  
    vendor_key: str | None = None  
    invoice_date: date | None = None
    currency: str | None = None
    subtotal_paise: int | None = None
    tax_paise: int | None = None
    total_paise: int | None = None


@dataclass(frozen=True)
class ValidationResult:
    invoice: NormalizedInvoice
    reasons: tuple[ReviewReason, ...] = field(default_factory=tuple)

    @property
    def status(self) -> str:
        return VALID if not self.reasons else NEEDS_REVIEW

    @property
    def is_valid(self) -> bool:
        return not self.reasons

    @property
    def reason_codes(self) -> list[str]:
        return [r.code for r in self.reasons]


def _normalize_amount(raw: str, field_name: str, reasons: list[ReviewReason]) -> int | None:
    try:
        return parse_money_to_paise(raw)
    except NormalizationError as exc:
        reasons.append(ReviewReason(exc.code, field_name, f"{field_name}: {exc}"))
        return None


def _paise_text(paise: int) -> str:
    return f"{paise // 100}.{paise % 100:02d}"


def validate(raw: RawInvoiceFields) -> ValidationResult:
    reasons: list[ReviewReason] = []
    values = raw.as_dict()

    
    for name in FIELD_LABELS:
        if values[name] is None:
            reasons.append(ReviewReason(f"missing_{name}", name, f"{name} was not found"))

    
    invoice_number = normalize_invoice_number(raw.invoice_number) if raw.invoice_number else None
    vendor = " ".join(raw.vendor.split()) if raw.vendor else None
    vendor_key = normalize_vendor(raw.vendor) if raw.vendor else None

    invoice_date = None
    if raw.date is not None:
        try:
            invoice_date = parse_date(raw.date)
        except NormalizationError as exc:
            reasons.append(ReviewReason(exc.code, "date", f"date: {exc}"))

    currency = None
    if raw.currency is not None:
        candidate = raw.currency.strip().upper()
        if _CURRENCY_PATTERN.match(candidate):
            currency = candidate
        else:
            reasons.append(
                ReviewReason("invalid_currency", "currency", f"currency: cannot read {raw.currency!r}")
            )

    subtotal = _normalize_amount(raw.subtotal, "subtotal", reasons) if raw.subtotal else None
    tax = _normalize_amount(raw.tax, "tax", reasons) if raw.tax else None
    total = _normalize_amount(raw.total, "total", reasons) if raw.total else None

    
    if subtotal is not None and tax is not None and total is not None and subtotal + tax != total:
        reasons.append(
            ReviewReason(
                "total_mismatch",
                "total",
                f"subtotal {_paise_text(subtotal)} + tax {_paise_text(tax)} = "
                f"{_paise_text(subtotal + tax)}, but total is {_paise_text(total)}",
            )
        )

    invoice = NormalizedInvoice(
        invoice_number=invoice_number,
        vendor=vendor,
        vendor_key=vendor_key,
        invoice_date=invoice_date,
        currency=currency,
        subtotal_paise=subtotal,
        tax_paise=tax,
        total_paise=total,
    )
    return ValidationResult(invoice=invoice, reasons=tuple(reasons))
