"""Evaluate top-k evidence and keep traces for independent manual audit."""
from .ingestion import normalize_text


def evaluate_query(question: dict, hits: list[dict]) -> dict:
    gold = [question, *question.get("alternative_gold", [])]
    labels = [
        any(hit["document_id"] == g["gold_source_id"] and hit["page"] == g["gold_page"]
            and normalize_text(g["evidence_quote"]) in normalize_text(hit["text"])
            for g in gold)
        for hit in hits[:3]
    ]
    return {**question, "hits": [dict(hit, evidence_hit=label) for hit, label in zip(hits, labels)],
            "hit1": bool(labels and labels[0]), "hit3": any(labels)}


def summarize(traces: list[dict]) -> dict:
    return {
        strategy: {
            split: {
                "total": len(rows),
                "hit1": sum(row["hit1"] for row in rows),
                "hit3": sum(row["hit3"] for row in rows),
            }
            for split in ("dev", "test")
            for rows in [[r for r in traces if r["strategy"] == strategy and r["split"] == split]]
        }
        for strategy in ("A", "B", "C")
    }
