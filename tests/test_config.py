from pathlib import Path

from pdf_rag.config import Settings


def test_defaults(monkeypatch):
    for name in ("DATA_DIR", "CHROMA_DIR", "LLM_MODEL", "TOP_K", "LLM_REASONING",
                 "OCR_LANG", "OCR_MODE", "OCR_DPI"):
        monkeypatch.delenv(name, raising=False)
    s = Settings.from_env()
    assert s.ocr.lang == "eng+mar" and s.ocr.mode == "auto" and s.ocr.dpi == 300
    assert s.llm_model == "qwen3:14b"
    assert s.chroma_dir == Path("data/chroma")
    assert s.pages_file == Path("data/processed/pages.jsonl")
    assert s.top_k == 5
    assert s.llm_reasoning is False


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("DATA_DIR", "/tmp/x")
    monkeypatch.delenv("CHROMA_DIR", raising=False)
    monkeypatch.setenv("LLM_MODEL", "qwen3:8b")
    monkeypatch.setenv("TOP_K", "8")
    monkeypatch.setenv("LLM_REASONING", "true")
    s = Settings.from_env()
    assert s.raw_dir == Path("/tmp/x/raw")
    assert s.chroma_dir == Path("/tmp/x/chroma")
    assert (s.llm_model, s.top_k, s.llm_reasoning) == ("qwen3:8b", 8, True)
