-- Invoice database schema (SQLite).
--
-- Duplicate key: (invoice_number, vendor_key)
--   invoice_number is trimmed and upper-cased; vendor_key is the vendor name
--   lower-cased with whitespace collapsed. The same invoice scanned twice, or
--   printed with different casing, therefore maps to ONE row in `invoices`.
--
-- Traceability: every scan of an invoice (including duplicate scans) gets its
-- own row in `source_scans`, linked to the invoice it belongs to.

CREATE TABLE IF NOT EXISTS invoices (
    id              INTEGER PRIMARY KEY,
    invoice_number  TEXT    NOT NULL,
    vendor          TEXT    NOT NULL,           -- as first printed
    vendor_key      TEXT    NOT NULL,
    invoice_date    TEXT    NOT NULL,           -- ISO 8601, YYYY-MM-DD
    currency        TEXT    NOT NULL,
    subtotal_paise  INTEGER NOT NULL CHECK (subtotal_paise >= 0),
    tax_paise       INTEGER NOT NULL CHECK (tax_paise >= 0),
    total_paise     INTEGER NOT NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (invoice_number, vendor_key),
    CHECK (subtotal_paise + tax_paise = total_paise)
);

CREATE TABLE IF NOT EXISTS source_scans (
    id            INTEGER PRIMARY KEY,
    invoice_id    INTEGER NOT NULL REFERENCES invoices(id),
    filename      TEXT    NOT NULL,
    sha256        TEXT    NOT NULL,             -- hash of the image file bytes
    raw_ocr_text  TEXT    NOT NULL,
    imported_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (sha256, filename)                   -- re-importing a file adds nothing
);

CREATE INDEX IF NOT EXISTS idx_source_scans_invoice ON source_scans(invoice_id);
