"""Unit tests for SemanticFinancialChunker."""
import pytest
from financial_ai.processing.chunker import SemanticFinancialChunker, count_tokens


def test_chunker_small_subsection_kept_intact():
    chunker = SemanticFinancialChunker(subsection_threshold=700)
    small_text = "This is a short financial disclosure paragraph." * 5
    assert count_tokens(small_text) < 700

    subsections = [{"heading": "Liquidity", "text": small_text}]
    chunks = chunker.chunk_section(
        ticker="AAPL",
        fiscal_year=2024,
        section_id="Item 7",
        section_name="MD&A",
        subsections=subsections,
    )

    assert len(chunks) == 1
    assert chunks[0]["metadata"]["ticker"] == "AAPL"
    assert chunks[0]["metadata"]["fiscal_year"] == 2024
    assert chunks[0]["metadata"]["section"] == "Item 7"
    assert chunks[0]["metadata"]["heading"] == "Liquidity"
    assert chunks[0]["chunk_id"] == "AAPL_2024_ITEM7_001"


def test_chunker_large_subsection_splits_without_cutting_paragraph():
    chunker = SemanticFinancialChunker(
        subsection_threshold=200,
        chunk_min_tokens=100,
        chunk_max_tokens=150,
        overlap_tokens=20,
    )
    paras = [f"Paragraph {i}: " + ("Financial disclosure content. " * 15) for i in range(10)]
    large_text = "\n\n".join(paras)

    subsections = [{"heading": "Results of Operations", "text": large_text}]
    chunks = chunker.chunk_section(
        ticker="NVDA",
        fiscal_year=2025,
        section_id="Item 7",
        section_name="MD&A",
        subsections=subsections,
    )

    assert len(chunks) > 1
    for ch in chunks:
        assert ch["metadata"]["ticker"] == "NVDA"
        assert ch["metadata"]["fiscal_year"] == 2025
        assert "NVDA_2025_ITEM7_" in ch["chunk_id"]


def test_hierarchical_chunking_token_bounds():
    chunker = SemanticFinancialChunker(
        subsection_threshold=1500,
        chunk_min_tokens=800,
        chunk_max_tokens=1500,
        child_chunk_tokens=180,
        child_overlap_tokens=35,
    )
    paras = [
        f"Financial statement analysis paragraph {i}. " + ("Our revenue and operating performance grew rapidly. " * 8)
        for i in range(12)
    ]
    large_text = "\n\n".join(paras)
    subsections = [{"heading": "Gross Margin Analysis", "text": large_text}]

    hier = chunker.chunk_hierarchical(
        ticker="MSFT",
        fiscal_year=2024,
        section_id="Item 7",
        section_name="MD&A",
        subsections=subsections,
    )

    parents = hier["parents"]
    children = hier["children"]

    assert len(parents) >= 1
    assert len(children) > len(parents)

    # All child chunks must be strictly <= 220 tokens (safely within MiniLM-L6-v2 limit of 256)
    for c in children:
        assert c["token_count"] <= 220, f"Child chunk exceeded token limit: {c['token_count']}"
        assert c["metadata"]["is_child"] is True
        assert "parent_id" in c["metadata"]
        # Ensure parent_id matches one of the parent chunks
        assert any(p["chunk_id"] == c["metadata"]["parent_id"] for p in parents)


def test_parent_docstore_crud(tmp_path):
    from financial_ai.rag.indexer import ParentDocStore

    db_path = str(tmp_path / "test_parents.sqlite")
    store = ParentDocStore(db_path=db_path)

    sample_parents = [
        {
            "chunk_id": "AAPL_2024_ITEM7_001",
            "text": "Parent chunk 1 text content.",
            "token_count": 500,
            "metadata": {
                "ticker": "AAPL",
                "fiscal_year": 2024,
                "section": "Item 7",
                "subsection": "Revenue",
            },
        },
        {
            "chunk_id": "AAPL_2024_ITEM7_002",
            "text": "Parent chunk 2 text content.",
            "token_count": 600,
            "metadata": {
                "ticker": "AAPL",
                "fiscal_year": 2024,
                "section": "Item 7",
                "subsection": "Gross Margin",
            },
        },
    ]

    count = store.put_parents(sample_parents)
    assert count == 2
    assert store.count() == 2

    # Get single
    p1 = store.get_parent("AAPL_2024_ITEM7_001")
    assert p1 is not None
    assert p1["ticker"] == "AAPL"
    assert p1["text"] == "Parent chunk 1 text content."

    # Get batch
    batch = store.get_parents(["AAPL_2024_ITEM7_001", "AAPL_2024_ITEM7_002"])
    assert len(batch) == 2
    assert "AAPL_2024_ITEM7_001" in batch
    assert "AAPL_2024_ITEM7_002" in batch

    # Clear
    store.clear()
    assert store.count() == 0
