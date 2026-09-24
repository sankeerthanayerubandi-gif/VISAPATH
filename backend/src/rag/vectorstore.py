"""
Builds and loads the ChromaDB vector store of official visa requirement
documents. This is the ONLY knowledge base the checklist agent is allowed
to draw requirements from — the LLM must never invent a requirement that
isn't retrievable here.
"""
import os
import datetime
from typing import List
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from backend.config.settings import (
    REQUIREMENTS_DIR,
    VECTOR_DB_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)
from backend.src.rag.embeddings import get_embeddings


def _load_requirement_files() -> List[Document]:
    """
    Loads every .txt requirement file in data/requirements/.
    Expected filename convention: <visa_category>__<source_name>.txt
    e.g. B-1-B-2__travel_state_gov_summary.txt
    """
    documents = []
    if not os.path.isdir(REQUIREMENTS_DIR):
        return documents

    for fname in os.listdir(REQUIREMENTS_DIR):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(REQUIREMENTS_DIR, fname)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        visa_category = fname.split("__")[0].replace("-", "/") if "__" in fname else "unknown"

        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": fname,
                    "visa_category": visa_category,
                    "country": "US",
                    "document_type": "official_requirement_sample",
                    "retrieval_date": str(datetime.date.today()),
                },
            )
        )
    return documents


def build_vectorstore() -> Chroma:
    """Splits requirement docs into chunks, embeds them, and persists to disk."""
    raw_docs = _load_requirement_files()
    if not raw_docs:
        raise ValueError(
            f"No requirement documents found in {REQUIREMENTS_DIR}. "
            "Add at least one .txt requirement file before building the knowledge base."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(raw_docs)

    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=VECTOR_DB_DIR,
    )
    return vectordb


def load_vectorstore() -> Chroma:
    """Loads an already-built vector store from disk without re-embedding."""
    if not os.path.exists(VECTOR_DB_DIR) or not os.listdir(VECTOR_DB_DIR):
        raise FileNotFoundError(
            "Vector database not found. Click 'Build/refresh knowledge base' first."
        )
    return Chroma(persist_directory=VECTOR_DB_DIR, embedding_function=get_embeddings())
