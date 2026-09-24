"""
Document extraction layer.
Supports PDF, DOCX, TXT. Preserves metadata (filename, page, doc type)
so findings can later be traced back to exact evidence.

Architecture note: to add OCR later for scanned PDFs, add a branch in
`_extract_pdf` that falls back to an OCR engine (e.g. pytesseract) when
a page yields no extractable text. No other file needs to change.
"""
import os
from typing import List
from pypdf import PdfReader
import docx

from backend.src.schemas.audit_schema import ExtractedDocument
from backend.src.security.injection_defense import scan_text


def _extract_pdf(filepath: str, filename: str) -> List[ExtractedDocument]:
    docs = []
    reader = PdfReader(filepath)
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            # Empty page text = likely a scanned image page.
            # OCR would be plugged in right here.
            text = "[No extractable text on this page — may require OCR.]"
        is_suspicious, _ = scan_text(text)
        docs.append(
            ExtractedDocument(
                filename=filename,
                document_type="pdf",
                page=i,
                text=text,
                is_suspicious=is_suspicious,
            )
        )
    return docs


def _extract_docx(filepath: str, filename: str) -> List[ExtractedDocument]:
    d = docx.Document(filepath)
    text = "\n".join(p.text for p in d.paragraphs)
    is_suspicious, _ = scan_text(text)
    return [
        ExtractedDocument(
            filename=filename,
            document_type="docx",
            page=None,
            text=text,
            is_suspicious=is_suspicious,
        )
    ]


def _extract_txt(filepath: str, filename: str) -> List[ExtractedDocument]:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    is_suspicious, _ = scan_text(text)
    return [
        ExtractedDocument(
            filename=filename,
            document_type="txt",
            page=None,
            text=text,
            is_suspicious=is_suspicious,
        )
    ]


def extract_document(filepath: str) -> List[ExtractedDocument]:
    """
    Extract text + metadata from a single file.
    Raises ValueError for unsupported formats or empty documents,
    so the caller (Streamlit UI) can show a friendly message.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    filename = os.path.basename(filepath)
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "pdf":
        results = _extract_pdf(filepath, filename)
    elif ext == "docx":
        results = _extract_docx(filepath, filename)
    elif ext == "txt":
        results = _extract_txt(filepath, filename)
    else:
        raise ValueError(f"Unsupported file format: .{ext}")

    if not any(r.text.strip() for r in results):
        raise ValueError(f"'{filename}' appears to be empty or unreadable.")

    return results


def extract_documents(filepaths: List[str]) -> List[ExtractedDocument]:
    """Extract a batch of uploaded files, collecting all pages/segments."""
    all_docs: List[ExtractedDocument] = []
    for fp in filepaths:
        all_docs.extend(extract_document(fp))
    return all_docs
