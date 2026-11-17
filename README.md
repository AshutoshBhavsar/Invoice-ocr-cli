# Invoice OCR CLI

A Python command-line application that extracts invoice information from images using local OCR, validates the extracted data, detects duplicate invoices, and stores valid records in SQLite.

The application uses Tesseract OCR locally, so it does not require paid OCR APIs.

## Features

- **Local OCR:** Extract text from invoice images using Tesseract.
- **Field extraction:** Identify invoice number, vendor, date, currency, subtotal, tax, and total.
- **Data normalization:** Standardize invoice numbers, vendor keys, dates, and monetary values.
- **Invoice validation:** Check required fields, date and amount formats, currency format, and subtotal-plus-tax consistency.
- **Duplicate detection:** Identify repeated invoices using normalized invoice number and vendor.
- **Conflict detection:** Flag invoices with matching identifiers but conflicting data.
- **SQLite storage:** Store valid invoices and associate their source scans.
- **Review handling:** Keep invalid or problematic invoices out of valid invoice storage.
- **JSON reports:** Generate processing summaries and a separate list of invoices requiring review.
- **Independent processing:** A failure on one image does not stop the remaining files from being processed.

## Technology Stack

- Python 3.10+
- Tesseract OCR
- pytesseract
- Pillow
- SQLite
- pytest

## Project Architecture

The application follows this processing pipeline:

```text
Invoice Images
      |
      v
OCR (ocr.py)
      |
      v
Field Extraction (parser.py)
      |
      v
Normalization (normalize.py)
      |
      v
Validation (validation.py)
      |
      v
Duplicate Detection & SQLite Storage (db.py)
      |
      v
JSON Reports (report.py)
```

The pipeline is coordinated by `pipeline.py` and executed through `cli.py`.

## Project Structure

```text
invoice-ocr-cli/
│
├── fixtures/                 # Sample invoice images
│
├── src/
│   └── invoice_ocr/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py             # Command-line interface
│       ├── ocr.py             # Image OCR and SHA-256 hashing
│       ├── parser.py          # Invoice field extraction
│       ├── normalize.py       # Data normalization
│       ├── validation.py      # Invoice validation
│       ├── db.py              # SQLite operations
│       ├── schema.sql         # Database schema
│       ├── pipeline.py        # End-to-end processing
│       └── report.py          # JSON report generation
│
├── tests/                    # Automated tests
├── docs/
│   ├── ARCHITECTURE.md
│   └── STATUS.md
│
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Installation

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd invoice-ocr-cli
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install the project

```powershell
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### 4. Install Tesseract OCR

Tesseract is a separate system dependency; installing `pytesseract` alone is not sufficient.

Install the Tesseract OCR executable for your operating system and make sure it is available through your system PATH.

Verify the installation:

```powershell
tesseract --version
```

## Usage

Run the application against a directory containing invoice images:

```powershell
python -m invoice_ocr run --input fixtures --db invoices.db --output output
```

Arguments:

| Argument | Description |
|---|---|
| `--input` | Directory containing invoice images (required) |
| `--db` | SQLite database file (default: `invoices.db`) |
| `--output` | Directory for generated reports (default: `output`) |

Supported image extensions: PNG, JPG, JPEG, TIF, TIFF, and BMP.

## Generated Reports

The application generates two JSON files inside the output directory:

- `report.json` — Processing summary and detailed results for every image, including extracted fields and normalized invoice data.
- `needs_review.json` — Files requiring manual review, with their review reasons.

## Sample Processing Results

The included synthetic fixtures demonstrate:

| Result | Count |
|---|---:|
| Valid invoices | 2 |
| Duplicate invoices | 1 |
| Invoices requiring review | 1 |
| Total files processed | 4 |

The invalid invoice is excluded from valid invoice storage. The database contains two unique invoices and three recorded source scans.

## Database Design

The SQLite database contains two primary tables:

- `invoices`: Stores unique, valid invoice records. A uniqueness constraint on invoice number and normalized vendor key helps prevent duplicate records.
- `source_scans`: Tracks individual source files associated with saved invoices. Multiple scans can refer to the same invoice.

Monetary values are stored as integer paise rather than floating-point values.

## Running Tests

Run the automated test suite:

```powershell
python -m pytest
```

The current test suite contains 54 tests covering OCR, parsing, normalization, validation, database operations, and end-to-end pipeline behavior.

## Limitations

- OCR accuracy depends on image quality and the Tesseract engine.
- Field extraction currently expects invoice information in the supported label-based format.
- Unsupported or incorrectly extracted values may require manual review.
- Tesseract must be installed separately on the machine running the application.

## Documentation

For more implementation details, design decisions, and database architecture, see:

- `docs/ARCHITECTURE.md`
- `docs/STATUS.md`
