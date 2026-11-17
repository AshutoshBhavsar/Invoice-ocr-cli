from __future__ import annotations
import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytesseract
from PIL import Image

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

TESSERACT_CONFIG = "--psm 6"


@dataclass(frozen=True)
class OcrResult:
    filename: str
    sha256: str
    text: str
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ocr_image(path: Path) -> OcrResult:
    try:
        digest = file_sha256(path)
    except OSError as exc:
        return OcrResult(path.name, "", "", f"cannot read file: {exc}")

    try:
        with Image.open(path) as img:
            text = pytesseract.image_to_string(img, config=TESSERACT_CONFIG)
    except Exception as exc:  # corrupt image, Tesseract missing, etc.
        return OcrResult(path.name, digest, "", f"{type(exc).__name__}: {exc}")

    return OcrResult(path.name, digest, text)


def find_images(directory: Path) -> list[Path]:
    return sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )


def ocr_directory(directory: Path) -> list[OcrResult]:
    return [ocr_image(p) for p in find_images(directory)]
