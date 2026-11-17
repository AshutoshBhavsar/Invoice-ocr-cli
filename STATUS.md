# Status log

## Step 1 - OCR + raw text capture (done)
- `ocr.py`, `cli.py`, `tests/test_ocr.py` (1 test).
- Finding: Tesseract read TNM-103's unclear total `11?0.00` as `1120.00`
  (confidently wrong). The subtotal + tax = total check must catch it.

## Step 2 - parser + normalization (done)
- `parser.py`: finds the 7 raw fields; missing -> None; odd values pass through.
- `normalize.py`: money -> int paise, dates -> date, vendor/invoice keys.
- Tests: 26 (`test_parser.py` 6, `test_normalize.py` 20), fixed OCR text in
  `tests/samples.py`. Total with step 1: 27.

## Step 3 - validation (done)
- `validation.py`: `validate(RawInvoiceFields) -> ValidationResult`.
- Collects ALL problems with reason codes: missing_<field>, invalid_amount,
  invalid_date, invalid_currency, total_mismatch.
- Sum check runs only when all three amounts were read (no misleading mismatch).
- Correctly-read values are kept even when the invoice needs review.
- Tests: 10 in `tests/test_validation.py`. Total: 37.

## Next - Step 4: db.py + schema.sql
- `invoices` unique on (invoice_number, vendor_key); `source_scans` links every
  scan (filename, sha256) to its invoice. Re-running must insert nothing new.
