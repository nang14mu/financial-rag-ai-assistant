"""Evidence Fusion module combining structured SQL tables and unstructured SEC text chunks."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class EvidenceContext(BaseModel):
    """Unified evidence container passed to the Answer Generator and Verifier."""
    user_query: str
    route: str
    sql_query: Optional[str] = None
    sql_rows: List[Dict[str, Any]] = Field(default_factory=list)
    sql_markdown: Optional[str] = None
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Serialize evidence into structured text for LLM generation."""
        sections = []

        if self.sql_markdown and self.sql_markdown.strip():
            sections.append(
                f"### [STRUCTURED FINANCIAL DATA (PostgreSQL Source)]\n"
                f"SQL Query Executed:\n```sql\n{self.sql_query}\n```\n\n"
                f"Results Table:\n{self.sql_markdown}"
            )

        if self.retrieved_chunks:
            chunk_texts = []
            for i, ch in enumerate(self.retrieved_chunks, 1):
                citation = ch.get("citation", "SEC 10-K")
                text = ch.get("text", "").strip()
                chunk_texts.append(f"Source [{i}] {citation}:\n{text}")

            sections.append(
                f"### [UNSTRUCTURED DISCLOSURES (SEC 10-K Chunks Source)]\n"
                + "\n\n---\n\n".join(chunk_texts)
            )

        if not sections:
            return "No evidence found in database or 10-K filings."

        return "\n\n=========================================\n\n".join(sections)


class EvidenceFusion:
    """Merges disparate evidence streams into a unified EvidenceContext."""

    def fuse(
        self,
        query: str,
        route: str,
        sql_result: Optional[Dict[str, Any]] = None,
        rag_result: Optional[List[Dict[str, Any]]] = None,
    ) -> EvidenceContext:
        """Construct fused evidence context."""
        sql_query = None
        sql_rows = []
        sql_md = None

        if sql_result:
            sql_query = sql_result.get("query")
            sql_rows = sql_result.get("rows", [])
            sql_md = sql_result.get("markdown_table")

        chunks = rag_result or []
        citations = [ch["citation"] for ch in chunks if "citation" in ch]

        return EvidenceContext(
            user_query=query,
            route=route,
            sql_query=sql_query,
            sql_rows=sql_rows,
            sql_markdown=sql_md,
            retrieved_chunks=chunks,
            citations=citations,
        )
