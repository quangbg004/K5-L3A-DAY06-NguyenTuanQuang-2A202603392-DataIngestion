"""Two page-preserving chunking strategies."""
from .models import Chunk, DocumentPage


def _chunk(page: DocumentPage, index: int, start: int, end: int) -> Chunk:
    return Chunk(
        f"{page.document_id}:{page.page}:{index}", page.document_id, page.source,
        page.page, page.text[start:end], {**page.metadata, "start": start, "end": end},
    )


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    if not 0 <= overlap < size:
        raise ValueError("Require 0 <= overlap < size")
    chunks = []
    for start in range(0, len(page.text), size - overlap):
        end = min(start + size, len(page.text))
        chunks.append(_chunk(page, len(chunks), start, end))
        if end == len(page.text):
            break
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    if max_size <= 0:
        raise ValueError("max_size must be positive")
    chunks = []
    start = 0
    while start < len(page.text):
        limit = min(start + max_size, len(page.text))
        end = limit
        if limit < len(page.text):
            for boundary in ("\n\n", ". ", " "):
                found = page.text.rfind(boundary, start + max_size // 3, limit)
                if found > start:
                    end = found + (1 if boundary == ". " else 0)
                    break
        chunks.append(_chunk(page, len(chunks), start, end))
        start = end
        while start < len(page.text) and page.text[start].isspace():
            start += 1
    return chunks
