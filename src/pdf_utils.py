"""Small helpers for getting text out of an uploaded document."""
from __future__ import annotations

import io

from pypdf import PdfReader


def text_from_pdf_bytes(data: bytes) -> str:
    """Extract text from a PDF given as raw bytes. Returns an empty string if nothing reads."""
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        if extracted.strip():
            pages.append(extracted)
    return "\n\n".join(pages).strip()


def read_document(name: str, data: bytes) -> str:
    """Dispatch on file extension. PDFs go through pypdf, everything else is decoded as text."""
    if name.lower().endswith(".pdf"):
        return text_from_pdf_bytes(data)
    try:
        return data.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""
