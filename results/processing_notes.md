# Data extraction and audit notes

- Survey pages 3–30 contain the body or conclusion. Page 30 is trimmed at the References heading. Pages 1–2 and 31–33 are excluded.
- A page-by-page check of pypdf layout extraction located rotated-text warnings on physical pages 1 and 33. Both pages are excluded.
- Among the retained pages, page 10 has merged words in the paragraph on MCP fragmentation, and page 19 interleaves the efficiency discussion with table content. The benchmark uses extracted text and does not assess figure graphics or table layout. All 30 retained units have non-empty text and all 20 gold excerpts were checked against the normalized sources.
- MCP Architecture (4,074 normalized characters) and MCP Lifecycle (5,952) each count as one independent source unit. Together with 28 PDF pages they give 30 units. The manifest links to the exact PDF version and the upstream MCP license notice at the same commit as both MDX snapshots.
- Coherence review was assisted by AI using the same midpoint of physical pages 3–12 for A and B. C inherits B's coherence labels because its chunk text is identical. Nguyễn Tuấn Quang manually reviewed the coherence, metadata and grounding audit tables on 2026-11-13 and confirmed the existing labels and findings.
- The holdout uses different survey pages from dev. One test item and one dev item share the MCP Lifecycle document, which can make generalization look stronger than it is.
