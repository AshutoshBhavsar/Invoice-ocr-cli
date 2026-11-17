"""Step 1 tests: a failing image must not stop the other files."""

from PIL import Image

from invoice_ocr import ocr


def test_bad_image_does_not_stop_other_files(tmp_path, monkeypatch):
    # fake the OCR engine so the test doesn't depend on the Tesseract version
    monkeypatch.setattr(ocr.pytesseract, "image_to_string", lambda *a, **k: "Invoice: X")

    Image.new("RGB", (10, 10), "white").save(tmp_path / "good.png")
    (tmp_path / "corrupt.png").write_bytes(b"this is not an image")

    results = {r.filename: r for r in ocr.ocr_directory(tmp_path)}

    assert results["good.png"].ok
    assert results["good.png"].text == "Invoice: X"
    assert not results["corrupt.png"].ok
    assert results["corrupt.png"].sha256  # still traceable to the file bytes
