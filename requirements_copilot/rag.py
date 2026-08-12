"""RAG pipeline over the requirements-engineering knowledge base.

Five explicit stages: load -> split -> embed -> store -> retrieve.

RAG strategy: **Hybrid**. Retrieval inside the reviewers is mandatory and deterministic
(2-Step), while `search_requirements_standards` is a tool an agent can call on demand
(Agentic). Pure Agentic was rejected because a reviewer that skips retrieval falls back on
its own taste, which is exactly the subjective judgement the Standards Reviewer exists to
replace. Pure 2-Step was rejected because ad-hoc lookups during synthesis are unpredictable
in topic and number.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .runtime import KNOWLEDGE_BASE_DIR

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# 1. LOAD
standards_docs = [
    Document(page_content=p.read_text(encoding="utf-8"), metadata={"source": str(p)})
    for p in sorted(Path(KNOWLEDGE_BASE_DIR).glob("**/*.md"))
]
if not standards_docs:
    raise FileNotFoundError(
        f"No knowledge-base documents found in {KNOWLEDGE_BASE_DIR}. "
        "Set COPILOT_DATA_DIR if the data directory lives elsewhere."
    )

# 2. SPLIT — heading separators first, so a chunk rarely straddles two rules
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=120,
    separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
)
standards_chunks = _splitter.split_documents(standards_docs)

# 3. EMBED — runs locally, no API key
embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

# 4. STORE
standards_store = InMemoryVectorStore.from_documents(standards_chunks, embeddings)

# 5. RETRIEVE
standards_retriever = standards_store.as_retriever(search_kwargs={"k": 4})


def retrieve_standards(query: str, k: int = 4) -> str:
    """Deterministic retrieval, used as step 1 inside the RAG-grounded reviewers."""
    hits = standards_store.similarity_search(query, k=k)
    if not hits:
        return "(no relevant standards retrieved)"
    return "\n\n---\n\n".join(
        f"[source: {Path(h.metadata['source']).name}]\n{h.page_content}" for h in hits
    )


@tool
def search_requirements_standards(query: str) -> str:
    """Search the requirements-engineering knowledge base for guidance relevant to a query.

    Contains quality criteria, the requirement-writing template and prohibited vague terms,
    a sample SRS exemplar, and catalogued conflict patterns. Use this to check how a
    requirement should be written, whether a term is disallowed, or what a correctly
    written equivalent looks like.
    """
    return retrieve_standards(query, k=4)


def pipeline_summary() -> dict:
    """Counts for the five stages, for logging or verification."""
    return {
        "documents": len(standards_docs),
        "chunks": len(standards_chunks),
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dim": len(embeddings.embed_query("probe")),
    }
