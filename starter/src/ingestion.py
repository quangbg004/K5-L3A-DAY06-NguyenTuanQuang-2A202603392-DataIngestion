"""Extract reproducible source units and retain physical PDF page numbers."""
import json
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

from .models import DocumentPage

PAPER_TITLE = "A Survey of AI Agent Protocols"
PAPER_URL = "https://arxiv.org/abs/2504.16736"
MCP_REV = "06e923405df3df242f1471b9300d9db90ebd10fd"
MCP_BASE = f"https://github.com/modelcontextprotocol/modelcontextprotocol/blob/{MCP_REV}/docs/specification/2025-03-26"
MCP_DOCS = [
    ("mcp-architecture", "MCP Architecture", "architecture/index.mdx"),
    ("mcp-lifecycle", "MCP Lifecycle", "basic/lifecycle.mdx"),
]


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=[a-z])", "", text)
    paragraphs = re.split(r"\n[ \t]*\n", text)
    return "\n\n".join(" ".join(p.split()) for p in paragraphs if p.strip())


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    pages = []
    for number, page in enumerate(PdfReader(path).pages, 1):
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except Exception as exc:
            raise ValueError(f"{path.name}, page {number}: extraction failed") from exc
        if number >= 3:
            text = re.sub(r"^\s*A Survey of AI Agent Protocols[^\S\n]*\n", "", text)
        text = re.sub(rf"\n\s*{number}\s*$", "", text)
        if number == 30:
            text = re.split(r"(?m)^\s*References\s*$", text, maxsplit=1)[0]
        pages.append(DocumentPage(document_id, source, number, normalize_text(text)))
    return pages


def load_corpus(data: Path) -> tuple[list[DocumentPage], dict]:
    physical = load_pdf(data / "2504.16736v3.pdf", "survey-v3", PAPER_URL)
    if len(physical) != 33:
        raise ValueError("Expected the 33-page arXiv v3 PDF")
    pages = physical[2:30]
    for page in pages:
        page.metadata["document_type"] = "survey"
    sources = [{
        "source_id": "survey-v3", "title": PAPER_TITLE,
        "source_path_or_url": PAPER_URL, "local_file": "2504.16736v3.pdf",
        "download_url": "https://arxiv.org/pdf/2504.16736v3",
        "license_or_permission": "CC BY 4.0",
        "license_url": "https://arxiv.org/html/2504.16736v3",
        "version": "2504.16736v3", "physical_pages": 33,
        "counting_rule": "Physical pages 3–30. Exclude front matter and references; remove References from mixed page 30.",
        "units": [{"page": p.page, "characters": len(p.text)} for p in pages],
    }]
    for source_id, title, remote_path in MCP_DOCS:
        filename = f"{source_id}.mdx"
        text = (data / filename).read_text(encoding="utf-8")
        text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.S)
        text = re.sub(r"(?ms)^```.*?^```[^\S\n]*$", "", text)
        text = normalize_text(text)
        if len(text) < 1500:
            raise ValueError(f"{filename} has fewer than 1500 normalized characters")
        url = f"{MCP_BASE}/{remote_path}"
        pages.append(DocumentPage(source_id, url, 1, text, {"document_type": "specification"}))
        sources.append({
            "source_id": source_id, "title": title, "source_path_or_url": url,
            "local_file": filename, "license_or_permission": "See upstream MIT/Apache-2.0 transition notice preserved with the snapshot",
            "license_notice": "starter/data/MCP-LICENSE", "version": MCP_REV,
            "license_url": f"https://github.com/modelcontextprotocol/modelcontextprotocol/blob/{MCP_REV}/LICENSE",
            "counting_rule": "One independent MDX document after removing front matter and fenced examples.",
            "units": [{"page": 1, "characters": len(text)}],
        })
    empty = [f"{p.document_id}:{p.page}" for p in pages if not p.text]
    if empty or len(pages) < 30:
        raise ValueError(f"Insufficient corpus or empty units: {empty}")
    return pages, {"accessed_at": "2026-11-13", "content_units": len(pages), "sources": sources}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    _, manifest = load_corpus(root / "starter" / "data")
    (root / "data" / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
