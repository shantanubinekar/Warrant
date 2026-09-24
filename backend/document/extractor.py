"""
Document text extraction — turns an uploaded prescription/report file into
plain text so it can go through the same LLM extraction pipeline as a
pasted clinical note.

Supported today: .pdf (text-based), .docx, .doc (best-effort), .txt/.md.
Scanned/image-only PDFs and photo uploads (.jpg/.png/.heic, etc.) are not
OCR'd — that needs a system OCR binary that isn't guaranteed to exist on
every deploy target, so we fail loudly with a clear message instead of
silently returning nothing.
"""

from __future__ import annotations

import io
from typing import Optional


class UnsupportedDocumentError(ValueError):
    """Raised when the uploaded file's format/content can't be turned into text."""


def extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from an uploaded file's raw bytes.

    Args:
        filename: Original filename (used only for its extension).
        content: Raw file bytes.

    Returns:
        Extracted plain text, stripped.

    Raises:
        UnsupportedDocumentError: If the format isn't supported, or if a
            supported format yields no usable text (e.g. a scanned PDF).
    """
    ext = (filename.rsplit(".", 1)[-1].lower() if "." in filename else "")

    if ext == "pdf":
        text = _extract_pdf(content)
    elif ext in ("docx",):
        text = _extract_docx(content)
    elif ext in ("txt", "md", "text"):
        text = _extract_plain_text(content)
    elif ext == "doc":
        raise UnsupportedDocumentError(
            "Legacy .doc files aren't supported — please save/export it as "
            ".docx or .pdf and upload that instead."
        )
    elif ext in ("jpg", "jpeg", "png", "heic", "webp", "gif", "bmp", "tiff"):
        raise UnsupportedDocumentError(
            "Image uploads (photos/scans) aren't supported yet — this reads "
            "text directly from files, it doesn't do OCR on pictures. Please "
            "upload a text-based PDF or DOCX, or paste the report text directly."
        )
    else:
        raise UnsupportedDocumentError(
            f"Unsupported file type '.{ext}'. Supported formats: PDF, DOCX, TXT."
        )

    text = (text or "").strip()
    if not text:
        raise UnsupportedDocumentError(
            "No readable text could be found in this file. If it's a scanned "
            "PDF (i.e. photos of pages rather than real text), please paste "
            "the report as text instead."
        )
    return text


def _extract_pdf(content: bytes) -> Optional[str]:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise UnsupportedDocumentError(
            "PDF support isn't installed on the server (missing pypdf)."
        ) from e

    reader = PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n\n".join(pages)


def _extract_docx(content: bytes) -> Optional[str]:
    try:
        import docx
    except ImportError as e:
        raise UnsupportedDocumentError(
            "DOCX support isn't installed on the server (missing python-docx)."
        ) from e

    document = docx.Document(io.BytesIO(content))
    parts = [p.text for p in document.paragraphs]

    # Tables often carry lab values (troponin, etc.) — include them too.
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))

    return "\n".join(parts)


def _extract_plain_text(content: bytes) -> Optional[str]:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None
