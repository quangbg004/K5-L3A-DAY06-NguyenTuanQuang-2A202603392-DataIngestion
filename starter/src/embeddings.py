"""Run a semantic embedding model locally on CPU."""
from pathlib import Path

from fastembed import TextEmbedding


class MyEmbedder:
    def __init__(self, model_name: str, cache_dir: str) -> None:
        self.model_name = model_name
        local = Path(cache_dir).parent / "bge-model"
        options = {"specific_model_path": str(local)} if (local / "model_optimized.onnx").is_file() else {}
        self.model = TextEmbedding(model_name=model_name, cache_dir=cache_dir, **options)
        self.dimensions = self.model.get_embedding_size(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self.model.passage_embed(texts, batch_size=32)]

    def embed_query(self, question: str) -> list[float]:
        return next(self.model.query_embed(question)).tolist()
