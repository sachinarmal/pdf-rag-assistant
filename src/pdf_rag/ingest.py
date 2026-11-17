"""Extract text (with OCR fallback and tables) from PDFs into page records."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from pathlib import Path

import pdfplumber
import pytesseract

log = logging.getLogger(__name__)

# Pages whose extracted text is shorter than this are treated as scans and OCR'd.
MIN_TEXT_CHARS = 30
OCR_RESOLUTION = 200


def clean(text: str | None) -> str:
    text = (text or "").replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def table_as_text(page) -> str:
    tables = []
    for table in page.extract_tables() or []:
        if table:
            tables.append("\n".join(
                " | ".join((str(c).strip() if c is not None else "") for c in row)
                for row in table
            ))
    return "\n\n".join(tables)


def extract_page(page, ocr_lang: str = "eng") -> tuple[str, str]:
    """Return (text, method) for one pdfplumber page."""
    text = clean(page.extract_text())
    method = "pdfplumber"
    if len(text) < MIN_TEXT_CHARS:
        try:
            ocr = clean(pytesseract.image_to_string(
                page.to_image(resolution=OCR_RESOLUTION).original, lang=ocr_lang
            ))
            if len(ocr) > len(text):
                text, method = ocr, "tesseract"
        except Exception as exc:  # tesseract missing, bad language pack, etc.
            log.warning("OCR skipped on page %s: %s", page.page_number, exc)
    tables = clean(table_as_text(page))
    if tables:
        text = (text + "\n\n[TABLE]\n" + tables).strip()
    return text, method


def extract_pdf(path: Path, ocr_lang: str = "eng") -> list[dict]:
    """Return one record per non-empty page: {"text": ..., "metadata": {...}}."""
    records = []
    log.info("Reading %s", path.name)
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, 1):
            text, method = extract_page(page, ocr_lang)
            if text:
                records.append({"text": text, "metadata": {
                    "source": path.name, "page": page_no, "method": method,
                }})
    return records


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_records(path: Path, records: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def ingest_files(pdfs: Iterable[Path], pages_file: Path, ocr_lang: str = "eng") -> list[dict]:
    """Extract the given PDFs and merge them into pages_file.

    Existing records for the same file names are replaced, so re-ingesting a
    file does not create duplicates. Returns only the new records.
    """
    new_records: list[dict] = []
    sources: set[str] = set()
    for pdf in pdfs:
        new_records.extend(extract_pdf(pdf, ocr_lang))
        sources.add(pdf.name)
    kept = [r for r in read_records(pages_file) if r["metadata"]["source"] not in sources]
    write_records(pages_file, kept + new_records)
    return new_records


def ingest_dir(raw_dir: Path, pages_file: Path, ocr_lang: str = "eng") -> list[dict]:
    """Extract every PDF in raw_dir, replacing pages_file entirely."""
    pdfs = sorted(raw_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDFs found in {raw_dir}/")
    records = [r for pdf in pdfs for r in extract_pdf(pdf, ocr_lang)]
    write_records(pages_file, records)
    return records
