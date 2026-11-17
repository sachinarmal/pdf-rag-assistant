# .ai Context Changelog

All notable changes to the `.ai/` context documentation. Newest first.

<!-- New entries go directly below this line, in this format:
## [YYYY-MM-DD] - <Task Name>
- **Scope**: <Modified files / directories>
- **Summary**: <Brief functional summary of changes>
- **Doc Updates**: <Which .ai/ context files were updated, or "none">
-->

## [0.1.0] - 2026-11-17 - Baseline snapshot
- **Scope**: `.ai/`, `CLAUDE.md` (documentation only; no code changes)
- **Summary**: First map of the code at commit `2affaa9`: the `pdf_rag` package (config, ingest with auto-OCR for garbled Devanagari, indexing, qa), the `pdf-rag` CLI, the Streamlit app, local `data/` storage and 19 pytest tests. Records the current `[AS-IS REALITY]` debt.
- **Doc Updates**: created `00-INDEX.md`, `layers/01-entrypoints.md`, `layers/02-domain-logic.md`, `layers/03-data-and-state.md`, `domains/.gitkeep`, and this changelog
