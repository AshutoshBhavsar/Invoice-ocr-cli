from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .ocr import OcrResult
from .validation import ValidationResult

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

INSERTED = "inserted"  
DUPLICATE = "duplicate"  
CONFLICT = "conflict"  


@dataclass(frozen=True)
class SaveResult:
    status: str
    invoice_id: int | None
    new_scan: bool = False
    message: str = ""


def connect(path: str | Path) -> sqlite3.Connection:
    """Open the database (``":memory:"`` works) and make sure the tables exist."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


def _values(inv) -> tuple:
    return (
        inv.invoice_date.isoformat(),
        inv.currency,
        inv.subtotal_paise,
        inv.tax_paise,
        inv.total_paise,
    )


def save_valid_invoice(
    conn: sqlite3.Connection, result: ValidationResult, scan: OcrResult
) -> SaveResult:
    """Store one valid invoice and its source scan in a single transaction."""
    if not result.is_valid:
        raise ValueError("only valid invoices can be stored; use the review report instead")

    inv = result.invoice
    key = (inv.invoice_number, inv.vendor_key)

    with conn:  
        cursor = conn.execute(
            """
            INSERT INTO invoices (invoice_number, vendor, vendor_key, invoice_date,
                                  currency, subtotal_paise, tax_paise, total_paise)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (invoice_number, vendor_key) DO NOTHING
            """,
            (inv.invoice_number, inv.vendor, inv.vendor_key, *_values(inv)),
        )
        is_new_invoice = cursor.rowcount == 1

        row = conn.execute(
            "SELECT * FROM invoices WHERE invoice_number = ? AND vendor_key = ?", key
        ).fetchone()

        if not is_new_invoice:
            stored = (
                row["invoice_date"],
                row["currency"],
                row["subtotal_paise"],
                row["tax_paise"],
                row["total_paise"],
            )
            if stored != _values(inv):
                return SaveResult(
                    CONFLICT,
                    row["id"],
                    message=(
                        f"invoice {inv.invoice_number} from this vendor is already stored "
                        "with different values"
                    ),
                )

        cursor = conn.execute(
            """
            INSERT INTO source_scans (invoice_id, filename, sha256, raw_ocr_text)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (sha256, filename) DO NOTHING
            """,
            (row["id"], scan.filename, scan.sha256, scan.text),
        )
        new_scan = cursor.rowcount == 1

    return SaveResult(INSERTED if is_new_invoice else DUPLICATE, row["id"], new_scan)


def count_invoices(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]


def scans_for_invoice(conn: sqlite3.Connection, invoice_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT filename FROM source_scans WHERE invoice_id = ? ORDER BY filename", (invoice_id,)
    ).fetchall()
    return [r["filename"] for r in rows]
