"""Unit tests for SectionParser."""
import pytest
from financial_ai.processing.section_parser import SectionParser


def test_section_parser_detects_items():
    parser = SectionParser()
    sample_10k_text = """
    TABLE OF CONTENTS
    Item 1. Business
    Item 1A. Risk Factors
    Item 7. Management's Discussion and Analysis

    ITEM 1. BUSINESS
    We design, manufacture, and market advanced accelerated computing systems.
    ### Overview
    Our accelerated computing platform is used worldwide.

    ITEM 1A. RISK FACTORS
    Competition in our industry is intense.
    ### Supply Chain
    We rely on third-party foundries.

    ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION
    ### Results of Operations
    Our revenue grew significantly due to Data Center demand.

    ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK
    Interest rate risk disclosures.
    """

    sections = parser.extract_sections(
        clean_text=sample_10k_text,
        ticker="TEST",
        fiscal_year=2024,
        save_to_disk=False,
    )

    assert "Item 1" in sections
    assert "Item 1A" in sections
    assert "Item 7" in sections
    assert len(sections["Item 1"]["subsections"]) > 0


def test_section_parser_preserves_paragraph_breaks():
    parser = SectionParser()
    text = (
        "Item 1. Business\n\n"
        "ITEM 1. BUSINESS\n"
        "Paragraph one describing business operations in detail.\n\n"
        "Paragraph two describing markets and distribution channels.\n\n"
        "Paragraph three describing competitive advantages.\n\n"
        "ITEM 1A. RISK FACTORS\n"
        "Risk factors text here."
    )
    sections = parser.extract_sections(text, ticker="TEST", fiscal_year=2024, save_to_disk=False)
    assert "Item 1" in sections
    subs = sections["Item 1"]["subsections"]
    assert len(subs) > 0
    # Must preserve \n\n between paragraphs
    assert "\n\n" in subs[0]["text"]
    assert "Paragraph one" in subs[0]["text"]
    assert "Paragraph two" in subs[0]["text"]
