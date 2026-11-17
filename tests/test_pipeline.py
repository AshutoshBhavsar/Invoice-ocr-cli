import json
from pathlib import Path

import pytest

from invoice_ocr import cli, db, pipeline
from invoice_ocr.ocr import OcrResult
from invoice_ocr.pipeline import STATUS_DUPLICATE, STATUS_NEEDS_REVIEW, STATUS_VALID, process_scan
from invoice_ocr.report import build_report

from samples import TNM_101, TNM_101_COPY, TNM_102, TNM_103_REVIEW

TEXTS = {
    "invoice-101.png": TNM_101,
    "invoice-101-copy.png": TNM_101_COPY,
    "invoice-102.png": TNM_102,
    "invoice-103-review.png": TNM_103_REVIEW,
}


def fake_ocr(path: Path) -> OcrResult:
    """Stands in for Tesseract so tests use fixed text."""
    return OcrResult(path.name, f"sha-{path.name}", TEXTS[path.name])


@pytest.fixture
def conn():
    connection = db.connect(":memory:")
    yield connection
    connection.close()


@pytest.fixture
def image_dir(tmp_path):
    folder = tmp_path / "images"
    folder.mkdir()
    for name in TEXTS:
        (folder / name).write_bytes(b"not a real image; OCR is faked")
    return folder


def test_valid_invoice_is_stored(conn):
    outcome = process_scan(conn, OcrResult("invoice-101.png", "aaa", TNM_101))
    assert outcome.status == STATUS_VALID
    assert outcome.invoice_id is not None
    assert db.count_invoices(conn) == 1


def test_rescanned_copy_is_reported_as_duplicate_of_the_same_invoice(conn):
    first = process_scan(conn, OcrResult("invoice-101.png", "aaa", TNM_101))
    copy = process_scan(conn, OcrResult("invoice-101-copy.png", "bbb", TNM_101_COPY))
    assert copy.status == STATUS_DUPLICATE
    assert copy.invoice_id == first.invoice_id


def test_incomplete_invoice_goes_to_review_with_reasons_and_is_not_stored(conn):
    outcome = process_scan(conn, OcrResult("invoice-103-review.png", "ccc", TNM_103_REVIEW))
    assert outcome.status == STATUS_NEEDS_REVIEW
    assert sorted(r.code for r in outcome.reasons) == ["invalid_date", "total_mismatch"]
    assert db.count_invoices(conn) == 0


def test_failed_ocr_is_reported_not_dropped(conn):
    outcome = process_scan(conn, OcrResult("broken.png", "ddd", "", "cannot identify image"))
    assert outcome.status == STATUS_NEEDS_REVIEW
    assert [r.code for r in outcome.reasons] == ["ocr_failed"]


def test_same_invoice_with_different_amounts_goes_to_review(conn):
    process_scan(conn, OcrResult("invoice-101.png", "aaa", TNM_101))
    changed = TNM_101.replace("1200.50", "1300.50").replace("216.09", "234.09").replace("1416.59", "1534.59")
    outcome = process_scan(conn, OcrResult("other.png", "eee", changed))
    assert outcome.status == STATUS_NEEDS_REVIEW
    assert [r.code for r in outcome.reasons] == ["duplicate_conflict"]


def test_one_crashing_file_does_not_stop_the_others(conn, image_dir):
    def flaky_ocr(path: Path) -> OcrResult:
        if path.name == "invoice-102.png":
            raise RuntimeError("boom")
        return fake_ocr(path)

    outcomes = {o.source_file: o for o in pipeline.run_pipeline(image_dir, conn, ocr=flaky_ocr)}

    assert len(outcomes) == 4  # every file is accounted for
    assert [r.code for r in outcomes["invoice-102.png"].reasons] == ["processing_error"]
    assert outcomes["invoice-101.png"].status in (STATUS_VALID, STATUS_DUPLICATE)
    assert db.count_invoices(conn) == 1  # 101 stored, 102 crashed, 103 needs review


def test_report_lists_each_file_with_status_reasons_and_filename(conn, image_dir):
    outcomes = pipeline.run_pipeline(image_dir, conn, ocr=fake_ocr)
    report = build_report(outcomes)

    assert report["summary"] == {"files": 4, "valid": 2, "duplicate": 1, "needs_review": 1}
    by_file = {f["source_file"]: f for f in report["files"]}
    assert set(by_file) == set(TEXTS)
    assert by_file["invoice-103-review.png"]["review_reasons"]
    assert by_file["invoice-102.png"]["normalized"]["total_paise"] == 177000
    json.dumps(report)  # must be JSON-serializable


def test_cli_run_twice_creates_no_duplicate_records(image_dir, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pipeline, "ocr_image", fake_ocr)
    db_path, out_dir = tmp_path / "invoices.db", tmp_path / "out"
    args = ["run", "--input", str(image_dir), "--db", str(db_path), "--output", str(out_dir)]

    assert cli.main(args) == 0
    assert cli.main(args) == 0  # second run on the same directory

    conn = db.connect(db_path)
    assert db.count_invoices(conn) == 2
    assert conn.execute("SELECT COUNT(*) FROM source_scans").fetchone()[0] == 3
    conn.close()

    report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert report["summary"]["valid"] == 0  # nothing new the second time
    review = json.loads((out_dir / "needs_review.json").read_text(encoding="utf-8"))
    assert [r["source_file"] for r in review] == ["invoice-103-review.png"]


def test_cli_reports_a_missing_input_directory(tmp_path, capsys):
    assert cli.main(["run", "--input", str(tmp_path / "nope")]) == 2
