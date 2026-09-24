"""Retrieval helpers used by the checklist agent."""
from typing import List
from langchain_core.documents import Document
from backend.config.settings import RETRIEVAL_K


def get_relevant_requirements(vectordb, visa_category: str, query: str) -> List[Document]:
    """
    Retrieve requirement chunks relevant to `query`, filtered to the
    selected visa category where metadata allows it.
    """
    retriever = vectordb.as_retriever(
        search_kwargs={
            "k": RETRIEVAL_K,
            "filter": {"visa_category": visa_category} if visa_category else None,
        }
    )
    try:
        results = retriever.invoke(query)
    except Exception:
        # Metadata filter can fail if categories don't match exactly —
        # fall back to an unfiltered search rather than crashing.
        retriever = vectordb.as_retriever(search_kwargs={"k": RETRIEVAL_K})
        results = retriever.invoke(query)
    return results


def format_context(docs: List[Document]) -> str:
    """Turn retrieved chunks into a labeled context block with provenance."""
    blocks = []
    for d in docs:
        src = d.metadata.get("source", "unknown_source")
        blocks.append(f"[SOURCE: {src}]\n{d.page_content}")
    return "\n\n".join(blocks)
