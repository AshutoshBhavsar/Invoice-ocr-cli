
"""Command line entry point.

    python -m invoice_ocr run --input fixtures --db invoices.db --output output
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import db
from .pipeline import run_pipeline
from .report import summary_line, write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="invoice-ocr",
        description="Extract invoice records from images using local OCR.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="process a directory of invoice images")
    run.add_argument("--input", type=Path, required=True, help="directory with images")
    run.add_argument(
        "--db",
        type=Path,
        default=Path("invoices.db"),
        help="SQLite database file",
    )
    run.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="directory for the reports",
    )
    return parser


def run(input_dir: Path, db_path: Path, output_dir: Path) -> int:
    if not input_dir.is_dir():
        print(f"error: input directory not found: {input_dir}", file=sys.stderr)
        return 2

    conn = db.connect(db_path)
    try:
        outcomes = run_pipeline(input_dir, conn)
    finally:
        conn.close()

    write_report(outcomes, output_dir)

    for outcome in outcomes:
        codes = ", ".join(r.code for r in outcome.reasons)
        detail = f"  ({codes})" if codes else ""
        print(f"{outcome.status:<13} {outcome.source_file}{detail}")

    print(summary_line(outcomes))
    print(f"reports written to {output_dir}/")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return run(args.input, args.db, args.output)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
