import sqlite3

import pytest

from invoice_ocr import db
from invoice_ocr.ocr import OcrResult
from invoice_ocr.parser import parse_fields
from invoice_ocr.validation import validate

from samples import TNM_101, TNM_101_COPY, TNM_102, TNM_103_REVIEW


def _scan(filename: str, text: str, sha: str) -> tuple:
    """Build the (validation result, scan) pair the pipeline would produce."""
    return validate(parse_fields(text)), OcrResult(filename, sha, text)


@pytest.fixture
def conn():
    connection = db.connect(":memory:")
    yield connection
    connection.close()


def test_first_import_stores_one_invoice_and_one_scan(conn):
    result = db.save_valid_invoice(conn, *_scan("invoice-101.png", TNM_101, "aaa"))

    assert result.status == db.INSERTED
    assert result.new_scan
    assert db.count_invoices(conn) == 1
    assert db.scans_for_invoice(conn, result.invoice_id) == ["invoice-101.png"]


def test_importing_the_same_file_again_adds_nothing(conn):
    first = db.save_valid_invoice(conn, *_scan("invoice-101.png", TNM_101, "aaa"))
    second = db.save_valid_invoice(conn, *_scan("invoice-101.png", TNM_101, "aaa"))

    assert second.status == db.DUPLICATE
    assert not second.new_scan
    assert db.count_invoices(conn) == 1
    assert len(db.scans_for_invoice(conn, first.invoice_id)) == 1


def test_rescanned_copy_is_one_invoice_with_two_traceable_scans(conn):
    original = db.save_valid_invoice(conn, *_scan("invoice-101.png", TNM_101, "aaa"))
    copy = db.save_valid_invoice(conn, *_scan("invoice-101-copy.png", TNM_101_COPY, "bbb"))

    assert copy.status == db.DUPLICATE
    assert copy.new_scan
    assert copy.invoice_id == original.invoice_id
    assert db.count_invoices(conn) == 1
    assert db.scans_for_invoice(conn, original.invoice_id) == [
        "invoice-101-copy.png",
        "invoice-101.png",
    ]


def test_different_invoices_are_stored_separately(conn):
    db.save_valid_invoice(conn, *_scan("invoice-101.png", TNM_101, "aaa"))
    db.save_valid_invoice(conn, *_scan("invoice-102.png", TNM_102, "ccc"))
    assert db.count_invoices(conn) == 2


def test_same_key_with_different_amounts_is_a_conflict_and_stores_nothing(conn):
    db.save_valid_invoice(conn, *_scan("invoice-101.png", TNM_101, "aaa"))
    changed = TNM_101.replace("1200.50", "1300.50").replace("216.09", "234.09").replace("1416.59", "1534.59")

    result = db.save_valid_invoice(conn, *_scan("other.png", changed, "ddd"))

    assert result.status == db.CONFLICT
    assert db.count_invoices(conn) == 1
    assert db.scans_for_invoice(conn, result.invoice_id) == ["invoice-101.png"]


def test_invoice_that_needs_review_cannot_be_stored(conn):
    with pytest.raises(ValueError):
        db.save_valid_invoice(conn, *_scan("invoice-103-review.png", TNM_103_REVIEW, "eee"))
    assert db.count_invoices(conn) == 0


def test_database_itself_rejects_a_total_that_does_not_add_up(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO invoices (invoice_number, vendor, vendor_key, invoice_date, currency,"
            " subtotal_paise, tax_paise, total_paise) VALUES ('X', 'v', 'v', '2026-10-01', 'INR', 100, 10, 999)"
        )


def test_running_on_a_file_database_twice_is_repeatable(tmp_path):
    path = tmp_path / "invoices.db"
    for _ in range(2):  # simulate running the program twice
        connection = db.connect(path)
        db.save_valid_invoice(connection, *_scan("invoice-101.png", TNM_101, "aaa"))
        connection.close()

    connection = db.connect(path)
    assert db.count_invoices(connection) == 1
    connection.close()
