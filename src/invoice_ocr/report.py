from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .pipeline import STATUS_DUPLICATE, STATUS_NEEDS_REVIEW, STATUS_VALID, FileOutcome


def build_report(outcomes: list[FileOutcome]) -> dict:
    counts = Counter(o.status for o in outcomes)
    return {
        "summary": {
            "files": len(outcomes),
            STATUS_VALID: counts[STATUS_VALID],
            STATUS_DUPLICATE: counts[STATUS_DUPLICATE],
            STATUS_NEEDS_REVIEW: counts[STATUS_NEEDS_REVIEW],
        },
        "files": [o.to_dict() for o in outcomes],
    }


def summary_line(outcomes: list[FileOutcome]) -> str:
    s = build_report(outcomes)["summary"]
    return (
        f"{s['files']} files: {s[STATUS_VALID]} valid, "
        f"{s[STATUS_DUPLICATE]} duplicate, {s[STATUS_NEEDS_REVIEW]} needs_review"
    )


def write_report(outcomes: list[FileOutcome], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(outcomes)

    review = [
        {
            "source_file": o.source_file,
            "review_reasons": [
                {"code": r.code, "field": r.field, "message": r.message} for r in o.reasons
            ],
        }
        for o in outcomes
        if o.status == STATUS_NEEDS_REVIEW
    ]

    _write_json(output_dir / "report.json", report)
    _write_json(output_dir / "needs_review.json", review)


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
