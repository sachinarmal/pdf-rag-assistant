# PDF RAG Assistant

Ask questions about your own PDFs and get answers with page citations, all running locally. Text is pulled from the PDFs (with OCR for scanned pages and table extraction), embedded with **bge-m3**, stored in **ChromaDB**, and answered by **Qwen3 14B** through **Ollama**. No data leaves your machine and no API keys are needed.

You can use it from the command line (`pdf-rag`) or through a Streamlit chat UI where you can also upload new PDFs.

## Architecture

```
            ┌──────────────┐   pages.jsonl   ┌──────────────┐  embeddings  ┌──────────┐
data/raw/ ─▶│  ingest.py   │────────────────▶│ indexing.py  │─────────────▶│ ChromaDB │
  *.pdf     │ pdfplumber   │ data/processed/ │ chunk 1000/150│  (bge-m3)   │data/chroma│
            │ + Tesseract  │                 └──────────────┘              └────┬─────┘
            │ + tables     │                                                    │ top-k
            └──────────────┘                                                    ▼
                                    question ──▶ ┌──────────────┐  prompt  ┌───────────┐
                     CLI / Streamlit ◀── answer ─│    qa.py     │─────────▶│ qwen3:14b │
                                    + sources    │ RagPipeline  │◀─────────│ (Ollama)  │
                                                 └──────────────┘          └───────────┘
```

1. **Ingest** (`pdf_rag.ingest`): reads each page with pdfplumber. Pages with fewer than 30 characters of text are treated as scans and run through Tesseract OCR. Tables are added as `a | b | c` rows under a `[TABLE]` marker. Each page becomes one JSON line with `source`, `page` and `method` metadata.
2. **Index** (`pdf_rag.indexing`): splits pages into overlapping chunks, embeds them with bge-m3 and stores them in a persistent Chroma collection. Re-indexing a file replaces its old chunks, so nothing is duplicated.
3. **Answer** (`pdf_rag.qa`): retrieves the top-k chunks for a question and asks Qwen3 to answer **only** from that context, citing `[filename, p. N]`. Any `<think>` reasoning text is removed before the answer is shown.

## Repository layout

```
├── src/pdf_rag/
│   ├── config.py       # settings from environment / .env
│   ├── ingest.py       # PDF → page records (text, OCR, tables)
│   ├── indexing.py     # chunking + Chroma index management
│   ├── qa.py           # retrieval + prompting (RagPipeline)
│   └── cli.py          # `pdf-rag` command
├── app/streamlit_app.py  # chat UI with PDF upload
├── tests/                # unit tests (no Ollama needed)
├── data/
│   ├── raw/            # your PDFs        (git-ignored)
│   ├── processed/      # pages.jsonl      (git-ignored)
│   └── chroma/         # vector store     (git-ignored)
├── .env.example
├── pyproject.toml
└── requirements.txt
```

## Setup

Requires macOS or Linux, Python 3.10+, and [Ollama](https://ollama.com).

```bash
# 1. Models (qwen3:14b needs about 10 GB of RAM; see "Configuration" for a lighter one)
ollama pull qwen3:14b
ollama pull bge-m3

# 2. Optional: OCR for scanned PDFs
brew install tesseract            # Debian/Ubuntu: sudo apt install tesseract-ocr

# 3. Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"           # or: pip install -r requirements.txt && pip install -e .

# 4. Optional: configuration
cp .env.example .env
```

Make sure Ollama is running (`ollama list` should work) before indexing or asking questions.

## Configuration

All settings come from environment variables or a `.env` file in the directory you run from. Every setting is optional.

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `LLM_MODEL` | `qwen3:14b` | Chat model (e.g. `qwen3:8b` for less memory) |
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature |
| `LLM_REASONING` | `false` | Let Qwen3 reason before answering (slower; the reasoning is not shown) |
| `EMBED_MODEL` | `bge-m3` | Embedding model |
| `DATA_DIR` | `data` | Root for `raw/` and `processed/` |
| `CHROMA_DIR` | `$DATA_DIR/chroma` | Vector store location |
| `COLLECTION_NAME` | `pdf_rag` | Chroma collection |
| `OCR_LANG` | `eng` | Tesseract languages, e.g. `eng+mar` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `150` | Text splitting, in characters |
| `TOP_K` | `5` | Chunks retrieved per question |

Changing `EMBED_MODEL`, `CHUNK_SIZE` or `CHUNK_OVERLAP` requires running `pdf-rag index` again.

## Usage

### Command line

```bash
cp ~/Downloads/*.pdf data/raw/

pdf-rag ingest          # extract text   → data/processed/pages.jsonl
pdf-rag index           # embed + store  → data/chroma/
pdf-rag ask "What is the session date?"
pdf-rag chat            # interactive; type `exit` or press Ctrl-D to quit
```

Example output:

```
$ pdf-rag ask "What date is this session?"

The date of the session is March 23, 2026 [MAR23-ASSEMBLY.pdf, p. 1].

Retrieved sources:
- MAR23-ASSEMBLY.pdf page 1
- MAR23-ASSEMBLY.pdf page 8
...
```

Add `-v` to any command to see progress logs. `python -m pdf_rag ...` works too.

### Web UI

```bash
streamlit run app/streamlit_app.py
```

Upload PDFs in the sidebar and click **Index**. They are saved to `data/raw/`, extracted and added to the index. Then ask questions in the chat. Each answer has a **Sources** section listing the pages it was built from.

### From Python

```python
from pdf_rag.config import get_settings
from pdf_rag.qa import RagPipeline

answer = RagPipeline(get_settings()).ask("Which ministers are listed?")
print(answer.text)
for doc in answer.sources:
    print(doc.metadata["source"], doc.metadata["page"])
```

## Testing

```bash
pytest
```

The unit tests replace Ollama, Chroma and Tesseract with fakes, so they run without any models installed.

## Known limitations

- **Text in non-Latin scripts.** Some PDFs, including many Marathi/Devanagari government documents, use fonts whose embedded text maps to the wrong characters. pdfplumber then returns readable-looking but garbled text, which hurts retrieval and translation quality. For those files, OCR usually works better: install the language pack (`brew install tesseract-lang`), set `OCR_LANG=eng+mar`, and force OCR by raising `MIN_TEXT_CHARS` in `ingest.py`.
- `pdf-rag ingest` and `pdf-rag index` rebuild everything from scratch. The web UI's upload adds or replaces individual files instead.
- Retrieval is plain vector similarity, with no reranking or hybrid keyword search.
