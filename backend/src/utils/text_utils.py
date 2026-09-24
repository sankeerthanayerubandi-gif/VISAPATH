"""Small, dependency-free text helpers used across the app."""
from typing import List
from backend.src.schemas.audit_schema import ExtractedDocument


def group_by_filename(documents: List[ExtractedDocument]) -> dict:
    """Group multi-page ExtractedDocument entries by filename for display."""
    grouped: dict = {}
    for doc in documents:
        grouped.setdefault(doc.filename, []).append(doc)
    return grouped


def truncate(text: str, max_len: int = 300) -> str:
    text = text.strip()
    return text if len(text) <= max_len else text[:max_len].rstrip() + "…"
