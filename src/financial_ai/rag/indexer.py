"""ChromaDB Indexer and SQLite ParentDocStore for Hierarchical SEC 10-K RAG."""
import os
import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)


class ParentDocStore:
    """Persistent SQLite store for full-context Parent Chunks."""

    def __init__(self, db_path: str = "./data/chroma_db/parent_store.sqlite"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS parent_chunks (
                    parent_id TEXT PRIMARY KEY,
                    ticker TEXT,
                    fiscal_year INTEGER,
                    section TEXT,
                    subsection TEXT,
                    text TEXT,
                    token_count INTEGER,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_parent_ticker_fy ON parent_chunks (ticker, fiscal_year);
            """)
            conn.commit()

    def put_parents(self, parents: List[Dict[str, Any]]) -> int:
        """Batch upsert Parent Chunks into SQLite."""
        if not parents:
            return 0

        rows = []
        for p in parents:
            meta = p.get("metadata", {})
            rows.append((
                p.get("chunk_id") or meta.get("chunk_id", ""),
                meta.get("ticker", ""),
                int(meta.get("fiscal_year", 0)),
                meta.get("section", ""),
                meta.get("subsection") or meta.get("heading", ""),
                p.get("text", ""),
                int(p.get("token_count", 0)),
                json.dumps(meta, ensure_ascii=False),
            ))

        with self._get_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO parent_chunks
                (parent_id, ticker, fiscal_year, section, subsection, text, token_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            conn.commit()

        logger.info("Persisted %d parent chunks to %s", len(rows), self.db_path)
        return len(rows)

    def get_parent(self, parent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single Parent Chunk by ID."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM parent_chunks WHERE parent_id = ?", (parent_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "chunk_id": row["parent_id"],
                "ticker": row["ticker"],
                "fiscal_year": row["fiscal_year"],
                "section": row["section"],
                "subsection": row["subsection"],
                "text": row["text"],
                "token_count": row["token_count"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            }

    def get_parents(self, parent_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Batch retrieve Parent Chunks by ID list."""
        if not parent_ids:
            return {}

        placeholders = ",".join(["?"] * len(parent_ids))
        result = {}
        with self._get_connection() as conn:
            cur = conn.execute(f"SELECT * FROM parent_chunks WHERE parent_id IN ({placeholders})", parent_ids)
            for row in cur.fetchall():
                result[row["parent_id"]] = {
                    "chunk_id": row["parent_id"],
                    "ticker": row["ticker"],
                    "fiscal_year": row["fiscal_year"],
                    "section": row["section"],
                    "subsection": row["subsection"],
                    "text": row["text"],
                    "token_count": row["token_count"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }
        return result

    def count(self) -> int:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM parent_chunks")
            return cur.fetchone()[0]

    def clear(self):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM parent_chunks")
            conn.commit()
        logger.info("Cleared all records from %s", self.db_path)


class ChromaIndexer:
    """Manages ChromaDB vector collections and ParentDocStore for hierarchical retrieval."""

    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "sec_10k_filings",
        parent_store_path: Optional[str] = None,
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        os.makedirs(self.persist_directory, exist_ok=True)

        parent_db = parent_store_path or os.path.join(self.persist_directory, "parent_store.sqlite")
        self.parent_store = ParentDocStore(db_path=parent_db)

        self.client = chromadb.PersistentClient(path=self.persist_directory)
        # Using default all-MiniLM-L6-v2 embedding function built into chromadb
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaIndexer initialized. Collection: '%s' (current count: %d), Parent store count: %d",
            self.collection_name,
            self.collection.count(),
            self.parent_store.count(),
        )

    def index_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """Batch index chunks into ChromaDB."""
        if not chunks:
            return 0

        total_indexed = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            ids = [c["chunk_id"] for c in batch]
            documents = [c["text"] for c in batch]
            metadatas = []
            for c in batch:
                meta = dict(c["metadata"])
                # Ensure all metadata values are primitive types supported by Chroma
                clean_meta = {}
                for k, v in meta.items():
                    if isinstance(v, (str, int, float, bool)):
                        clean_meta[k] = v
                    elif v is None:
                        clean_meta[k] = ""
                    else:
                        clean_meta[k] = str(v)
                metadatas.append(clean_meta)

            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            total_indexed += len(batch)

        logger.info("Successfully indexed %d chunks into ChromaDB '%s'.", total_indexed, self.collection_name)
        return total_indexed

    def index_hierarchical(
        self,
        parents: List[Dict[str, Any]],
        children: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> Tuple[int, int]:
        """Index Parent Chunks into SQLite ParentDocStore and Child Chunks into ChromaDB."""
        parent_count = self.parent_store.put_parents(parents)
        child_count = self.index_chunks(children, batch_size=batch_size)
        logger.info("Hierarchical indexing completed: %d parents stored, %d children vector-indexed.", parent_count, child_count)
        return parent_count, child_count

    def count(self) -> int:
        return self.collection.count()

    def reset(self):
        """Reset both ChromaDB collection and ParentDocStore."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        self.parent_store.clear()
        logger.info("Reset collection '%s' and parent store.", self.collection_name)
