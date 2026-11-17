
# Invoice OCR CLI — Architecture

## Overview

A local Python command-line application that extracts invoice information
from images, validates the extracted data, detects duplicates, and stores
valid invoices in SQLite.

No paid OCR APIs are required. OCR is performed locally using Tesseract.

## Processing pipeline

Image files
    ↓
OCR — ocr.py
    ↓
Field extraction — parser.py
    ↓
Normalization — normalize.py
    ↓
Validation — validation.py
    ↓
Duplicate detection and storage — db.py
    ↓
Reports — report.py

The pipeline is coordinated by pipeline.py and invoked through cli.py.

## Main modules

- ocr.py: Reads invoice images and extracts text using Tesseract.
- parser.py: Extracts invoice number, vendor, date, currency and amounts.
- normalize.py: Normalizes dates, vendor names, invoice numbers and money.
- validation.py: Checks required fields, dates, currencies and amount consistency.
- db.py: Manages SQLite storage and duplicate detection.
- pipeline.py: Coordinates processing for each invoice file.
- report.py: Generates JSON processing reports.
- cli.py: Provides the command-line interface.

## Database design

The database contains two main tables:

### invoices
Stores unique, valid invoices.

A unique constraint on invoice number and normalized vendor key
prevents duplicate invoice records.

### source_scans
Stores the source files associated with saved invoices.

Multiple scans can refer to the same invoice.

## Important design decisions

- Money is stored as integer paise rather than floating-point values.
- Invalid invoices are not inserted into the invoices table.
- Duplicate detection uses normalized invoice number and vendor.
- Conflicting invoice data is sent for review.
- Each file is processed independently so one processing failure
  does not stop the remaining files.
- OCR and processing errors are recorded for review.

## Running the application

```powershell
python -m invoice_ocr run --input fixtures --db invoices.db --output output
```

## Generated reports

- output/report.json: Processing summary and details for every file.
- output/needs_review.json: Files requiring manual review.
