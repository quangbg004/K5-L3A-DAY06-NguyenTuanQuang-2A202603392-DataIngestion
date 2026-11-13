"""Run the three retrieval strategies on a frozen dev/test benchmark."""
import argparse
import hashlib
import json
import os
from importlib.metadata import version
from pathlib import Path
from statistics import median
from time import perf_counter

from .chunking import by_paragraph, fixed_size
from .evaluation import evaluate_query, summarize
from .ingestion import load_corpus

ROOT = Path(__file__).resolve().parents[2]
STARTER = ROOT / "starter"
MODEL = "BAAI/bge-small-en-v1.5"


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare():
    pages, manifest = load_corpus(STARTER / "data")
    benchmark = (ROOT / "benchmark" / "questions.json").read_bytes()
    questions = json.loads(benchmark)
    lookup = {(p.document_id, p.page): p for p in pages}
    if len({q["id"] for q in questions}) != len(questions):
        raise ValueError("Duplicate question IDs")
    if any(q["split"] not in {"dev", "test"} for q in questions):
        raise ValueError("Unknown benchmark split")
    if sum(q["split"] == "dev" for q in questions) < 15 or sum(q["split"] == "test" for q in questions) < 5:
        raise ValueError("Need at least 15 dev and 5 test questions")
    filtered = [q for q in questions if q.get("filter")]
    if len(filtered) < 3 or not any(q["split"] == "test" for q in filtered):
        raise ValueError("Need three filter questions, including a test question")
    for q in questions:
        page = lookup[q["gold_source_id"], q["gold_page"]]
        if not q["evidence_quote"] or q["evidence_quote"] not in page.text:
            raise ValueError(f"Missing gold evidence for {q['id']}")
        if any(page.metadata.get(k) != v for k, v in q.get("filter", {}).items()):
            raise ValueError(f"Gold page is outside the question filter: {q['id']}")
    return pages, manifest, questions, hashlib.sha256(benchmark).hexdigest()


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true", help="Validate sources and gold; export chunk samples")
    args = parser.parse_args()
    pages, manifest, questions, benchmark_hash = prepare()
    output = ROOT / "results"
    output.mkdir(exist_ok=True)
    write_json(ROOT / "data" / "manifest.json", manifest)
    groups = {}
    stats = {}
    samples = []
    for strategy, chunker in (
        ("A", lambda p: fixed_size(p, 500, 50)),
        ("B", lambda p: by_paragraph(p, 500)),
    ):
        start = perf_counter()
        groups[strategy] = [chunk for page in pages for chunk in chunker(page)]
        lengths = [len(c.text) for c in groups[strategy]]
        stats[strategy] = {
            "chunk_count": len(lengths), "total_characters": sum(lengths),
            "min_characters": min(lengths), "median_characters": median(lengths),
            "max_characters": max(lengths), "chunk_seconds": perf_counter() - start,
        }
        for page in pages[:10]:
            offset = len(page.text) // 2
            covering = [c for c in groups[strategy] if c.document_id == page.document_id
                        and c.page == page.page and c.metadata["start"] <= offset < c.metadata["end"]]
            # If a chunker skipped whitespace at the midpoint, use the nearest following character.
            if not covering:
                offset = next(i for i in range(offset, len(page.text)) if not page.text[i].isspace())
                covering = [c for c in groups[strategy] if c.document_id == page.document_id
                            and c.page == page.page and c.metadata["start"] <= offset < c.metadata["end"]]
            samples.append({"strategy": strategy, "source": page.document_id, "page": page.page,
                            "offset": offset, "chunks": [{"id": c.chunk_id, "text": c.text} for c in covering]})
    write_json(output / "chunk_stats.json", stats)
    write_json(output / "coherence_samples.json", samples)
    if args.prepare_only:
        print(f"Validated {len(pages)} source units and {len(questions)} questions. SHA-256: {benchmark_hash}")
        return

    from dotenv import load_dotenv
    from .embeddings import MyEmbedder
    from .store import PgVectorStore

    load_dotenv(STARTER / ".env")
    embedder = MyEmbedder(MODEL, str(STARTER / ".venv" / "model-cache"))
    store = PgVectorStore(os.environ["DATABASE_URL"], embedder.dimensions)
    versions = store.create_schema()
    for strategy, chunks in groups.items():
        start = perf_counter()
        vectors = embedder.embed_documents([c.text for c in chunks])
        initial = store.upsert(strategy, chunks, vectors)
        stats[strategy]["embed_and_store_seconds"] = perf_counter() - start
        repeated = store.upsert(strategy, chunks, vectors)
        if initial != repeated or repeated != len(chunks):
            raise RuntimeError(f"Idempotence check failed for {strategy}")
        stats[strategy]["reingest_count"] = repeated
    stats["C"] = {"chunk_count": stats["B"]["chunk_count"], "reuses_index": "B"}

    traces = []
    for split in ("dev", "test"):
        for q in (item for item in questions if item["split"] == split):
            vector = embedder.embed_query(q["question"])
            for strategy in ("A", "B", "C"):
                filters = q.get("filter") if strategy == "C" else None
                hits = store.search("B" if strategy == "C" else strategy, vector, filters=filters)
                traces.append(dict(evaluate_query(q, hits), strategy=strategy, applied_filter=filters))
        if split == "dev":
            dev = summarize(traces)
            winner = max(("A", "B", "C"), key=lambda s: (dev[s]["dev"]["hit3"], dev[s]["dev"]["hit1"]))
            write_json(output / "dev_selection.json", {
                "strategy": winner, "rule": "Highest dev Hit@3, then Hit@1, then A/B/C order",
                "benchmark_sha256": benchmark_hash,
            })
    write_json(output / "traces.json", traces)
    write_json(output / "benchmark_metrics.json", {
        "benchmark_sha256": benchmark_hash, "selected_on_dev": winner, "model": MODEL,
        "dimensions": embedder.dimensions, "fastembed": version("fastembed"),
        "pypdf": version("pypdf"), "database": versions, "paid_api_cost": 0,
        "search": "exact cosine", "strategies": stats, "metrics": summarize(traces),
    })


if __name__ == "__main__":
    run()
