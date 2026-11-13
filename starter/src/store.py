"""Persistent PostgreSQL storage with exact cosine search."""
import json
import math

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        self.database_url = database_url
        self.dimensions = int(dimensions)
        if self.dimensions < 1:
            raise ValueError("Invalid vector dimension")

    def connect(self):
        return psycopg.connect(self.database_url, connect_timeout=5, row_factory=dict_row)

    def create_schema(self) -> dict:
        with self.connect() as connection:
            versions = connection.execute(
                "SELECT current_setting('server_version') AS postgres, extversion AS pgvector "
                "FROM pg_extension WHERE extname = 'vector'"
            ).fetchone()
            if versions is None:
                raise RuntimeError("pgvector extension missing")
            connection.execute(f"""
                CREATE TABLE IF NOT EXISTS day06_protocol_chunks (
                    strategy text NOT NULL, chunk_id text NOT NULL,
                    document_id text NOT NULL, source text NOT NULL, page integer NOT NULL,
                    text text NOT NULL, metadata jsonb NOT NULL,
                    embedding vector({self.dimensions}) NOT NULL,
                    PRIMARY KEY (strategy, chunk_id)
                )
            """)
            return versions

    def _vector(self, vector: list[float]) -> str:
        if len(vector) != self.dimensions or not all(math.isfinite(v) for v in vector):
            raise ValueError("Invalid embedding shape or values")
        return json.dumps(vector)

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> int:
        rows = [
            (strategy, c.chunk_id, c.document_id, c.source, c.page, c.text,
             Jsonb(c.metadata), self._vector(v))
            for c, v in zip(chunks, vectors, strict=True)
        ]
        with self.connect() as connection, connection.cursor() as cursor:
            # Serialize replacements, including the first ingest of an empty index.
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"day06:{strategy}",))
            cursor.execute("DELETE FROM day06_protocol_chunks WHERE strategy = %s", (strategy,))
            cursor.executemany("""
                INSERT INTO day06_protocol_chunks VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector)
            """, rows)
            cursor.execute("SELECT count(*) AS n FROM day06_protocol_chunks WHERE strategy = %s",
                           (strategy,))
            return cursor.fetchone()["n"]

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict | None = None) -> list[dict]:
        vector = self._vector(query_vector)
        with self.connect() as connection:
            return connection.execute("""
                SELECT chunk_id, document_id, source, page, text, metadata,
                       1 - (embedding <=> %s::vector) AS score
                FROM day06_protocol_chunks
                WHERE strategy = %s AND metadata @> %s
                ORDER BY score DESC, chunk_id
                LIMIT %s
            """, (vector, strategy, Jsonb(filters or {}), top_k)).fetchall()
