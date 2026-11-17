"""Command line entry point.

Step 1: OCR every image in a directory and write the raw text to JSON.
Later steps will extend ``run`` with parsing, validation and the database.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ocr import ocr_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="invoice-ocr",
        description="Extract invoice records from images using local OCR.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="process a directory of invoice images")
    run.add_argument("--input", type=Path, required=True, help="directory with images")
    run.add_argument(
        "--output", type=Path, default=Path("output"), help="directory for reports"
    )
    return parser


def run(input_dir: Path, output_dir: Path) -> int:
    if not input_dir.is_dir():
        print(f"error: input directory not found: {input_dir}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    results = ocr_directory(input_dir)

    raw = [
        {
            "source_file": r.filename,
            "sha256": r.sha256,
            "raw_ocr_text": r.text,
            "ocr_error": r.error,
        }
        for r in results
    ]
    (output_dir / "raw_ocr.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    failed = [r.filename for r in results if not r.ok]
    print(f"OCR done: {len(results) - len(failed)} ok, {len(failed)} failed")
    for name in failed:
        print(f"  failed: {name}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return run(args.input, args.output)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
