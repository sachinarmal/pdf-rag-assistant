from types import SimpleNamespace

import pdf_rag.ingest as ingest


class FakePage:
    def __init__(self, text, tables=None, page_number=1):
        self._text = text
        self._tables = tables or []
        self.page_number = page_number

    def extract_text(self):
        return self._text

    def extract_tables(self):
        return self._tables

    def to_image(self, resolution):
        return SimpleNamespace(original=object())


def test_clean_collapses_whitespace_and_nulls():
    assert ingest.clean("a\x00b   c\t\td\n\n\n\n\ne ") == "ab c d\n\ne"
    assert ingest.clean(None) == ""


def test_table_as_text_handles_none_cells():
    page = FakePage("", tables=[[["a", None], [" b ", "c"]], []])
    assert ingest.table_as_text(page) == "a | \nb | c"


def test_extract_page_uses_text_when_long_enough():
    page = FakePage("x" * 50)
    assert ingest.extract_page(page) == ("x" * 50, "pdfplumber")


def test_extract_page_falls_back_to_ocr(monkeypatch):
    monkeypatch.setattr(ingest.pytesseract, "image_to_string", lambda img, lang: "scanned text here")
    text, method = ingest.extract_page(FakePage(""))
    assert (text, method) == ("scanned text here", "tesseract")


def test_extract_page_survives_ocr_failure(monkeypatch):
    def boom(img, lang):
        raise RuntimeError("tesseract not installed")

    monkeypatch.setattr(ingest.pytesseract, "image_to_string", boom)
    text, method = ingest.extract_page(FakePage("short", tables=[[["k", "v"]]]))
    assert method == "pdfplumber"
    assert text == "short\n\n[TABLE]\nk | v"


def test_ingest_files_replaces_records_for_same_source(tmp_path, monkeypatch):
    pages_file = tmp_path / "pages.jsonl"
    ingest.write_records(pages_file, [
        {"text": "old", "metadata": {"source": "a.pdf", "page": 1}},
        {"text": "keep", "metadata": {"source": "b.pdf", "page": 1}},
    ])
    monkeypatch.setattr(ingest, "extract_pdf", lambda p, lang: [
        {"text": "new", "metadata": {"source": p.name, "page": 1}}
    ])
    new = ingest.ingest_files([tmp_path / "a.pdf"], pages_file)
    assert [r["text"] for r in new] == ["new"]
    assert sorted(r["text"] for r in ingest.read_records(pages_file)) == ["keep", "new"]
