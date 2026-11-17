from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import db
from .ocr import OcrResult, find_images, ocr_image
from .parser import parse_fields
from .validation import NormalizedInvoice, ReviewReason, validate

STATUS_VALID = "valid"  
STATUS_DUPLICATE = "duplicate" 
STATUS_NEEDS_REVIEW = "needs_review"  


@dataclass(frozen=True)
class FileOutcome:
    source_file: str
    status: str
    sha256: str = ""
    raw_ocr_text: str = ""
    raw_fields: dict = field(default_factory=dict)
    invoice: NormalizedInvoice | None = None
    reasons: tuple[ReviewReason, ...] = ()
    invoice_id: int | None = None

    def to_dict(self) -> dict:
        inv = self.invoice
        return {
            "source_file": self.source_file,
            "sha256": self.sha256,
            "status": self.status,
            "invoice_id": self.invoice_id,
            "raw_fields": self.raw_fields,
            "normalized": None
            if inv is None
            else {
                "invoice_number": inv.invoice_number,
                "vendor": inv.vendor,
                "vendor_key": inv.vendor_key,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "currency": inv.currency,
                "subtotal_paise": inv.subtotal_paise,
                "tax_paise": inv.tax_paise,
                "total_paise": inv.total_paise,
            },
            "review_reasons": [
                {"code": r.code, "field": r.field, "message": r.message} for r in self.reasons
            ],
            "raw_ocr_text": self.raw_ocr_text,
        }


def process_scan(conn: sqlite3.Connection, scan: OcrResult) -> FileOutcome:
    
    if not scan.ok:
        reason = ReviewReason("ocr_failed", None, f"OCR failed: {scan.error}")
        return FileOutcome(scan.filename, STATUS_NEEDS_REVIEW, scan.sha256, reasons=(reason,))

    raw = parse_fields(scan.text)
    result = validate(raw)
    common = dict(
        source_file=scan.filename,
        sha256=scan.sha256,
        raw_ocr_text=scan.text,
        raw_fields=raw.as_dict(),
        invoice=result.invoice,
    )

    if not result.is_valid:
        return FileOutcome(status=STATUS_NEEDS_REVIEW, reasons=result.reasons, **common)

    saved = db.save_valid_invoice(conn, result, scan)
    if saved.status == db.CONFLICT:
        reason = ReviewReason("duplicate_conflict", None, saved.message)
        return FileOutcome(
            status=STATUS_NEEDS_REVIEW, reasons=(reason,), invoice_id=saved.invoice_id, **common
        )

    status = STATUS_VALID if saved.status == db.INSERTED else STATUS_DUPLICATE
    return FileOutcome(status=status, invoice_id=saved.invoice_id, **common)


def run_pipeline(
    input_dir: Path,
    conn: sqlite3.Connection,
    ocr: Callable[[Path], OcrResult] | None = None,
) -> list[FileOutcome]:
    ocr_fn = ocr if ocr is not None else ocr_image
    outcomes: list[FileOutcome] = []

    for path in find_images(input_dir):
        try:
            outcomes.append(process_scan(conn, ocr_fn(path)))
        except Exception as exc: 
            reason = ReviewReason("processing_error", None, f"{type(exc).__name__}: {exc}")
            outcomes.append(FileOutcome(path.name, STATUS_NEEDS_REVIEW, reasons=(reason,)))

    return outcomes
