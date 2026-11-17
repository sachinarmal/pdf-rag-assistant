from pathlib import Path
from types import SimpleNamespace

from langchain_core.documents import Document

from pdf_rag.config import Settings
from pdf_rag.qa import RagPipeline, build_messages, format_context, strip_think


def make_settings(**overrides) -> Settings:
    base = dict(
        ollama_base_url="http://localhost:11434", llm_model="m", llm_temperature=0.0,
        llm_reasoning=False, embed_model="e", data_dir=Path("data"),
        chroma_dir=Path("data/chroma"), collection_name="c", ocr_lang="eng",
        chunk_size=1000, chunk_overlap=150, top_k=3,
    )
    return Settings(**{**base, **overrides})


DOCS = [
    Document(page_content="alpha", metadata={"source": "a.pdf", "page": 2}),
    Document(page_content="beta", metadata={}),
]


def test_strip_think():
    assert strip_think("<think>\nhmm\n</think>\n\nAnswer") == "Answer"
    assert strip_think("No tags") == "No tags"


def test_format_context_includes_citations():
    assert format_context(DOCS) == "[a.pdf, p. 2]\nalpha\n\n[?, p. ?]\nbeta"


def test_build_messages_has_system_and_question():
    system, human = build_messages("What?", DOCS)
    assert "Answer only from retrieved context" in system.content
    assert human.content.endswith("QUESTION: What?")


class FakeStore:
    def __init__(self, docs):
        self.docs = docs
        self.k = None

    def similarity_search(self, q, k):
        self.k = k
        return self.docs


class FakeLLM:
    def __init__(self):
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return SimpleNamespace(content="<think>x</think>It is alpha [a.pdf, p. 2]")


def test_pipeline_ask_uses_top_k_and_strips_think():
    store, llm = FakeStore(DOCS), FakeLLM()
    answer = RagPipeline(make_settings(top_k=7), store=store, llm=llm).ask("q")
    assert store.k == 7
    assert answer.text == "It is alpha [a.pdf, p. 2]"
    assert answer.sources == DOCS


def test_pipeline_ask_with_empty_index_skips_llm():
    llm = FakeLLM()
    answer = RagPipeline(make_settings(), store=FakeStore([]), llm=llm).ask("q")
    assert "empty" in answer.text
    assert llm.messages is None
