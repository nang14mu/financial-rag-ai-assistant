"""Parser for extracting major sections (Item 1, Item 1A, Item 7) from cleaned SEC 10-K text."""
import os
import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

SECTIONS_CONFIG = [
    {
        "id": "Item 1",
        "name": "Business",
        "pattern": r"(?:ITEM|Item)\s+1[\.\:\s\-\_]+(?:B\s*USINESS|Business)",
        "next_pattern": r"(?:ITEM|Item)\s+1A[\.\:\s\-\_]+(?:R\s*ISK\s+FACTORS|Risk\s+Factors)",
    },
    {
        "id": "Item 1A",
        "name": "Risk Factors",
        "pattern": r"(?:ITEM|Item)\s+1A[\.\:\s\-\_]+(?:R\s*ISK\s+FACTORS|Risk\s+Factors)",
        "next_pattern": r"(?:ITEM|Item)\s+(?:1B|1C|2)[\.\:\s\-\_]+",
    },
    {
        "id": "Item 7",
        "name": "MD&A",
        "pattern": r"(?:ITEM|Item)\s+7[\.\:\s\-\_]+(?:M\s*ANAGEMENT[\'’]S\s+DISCUSSION|Management[\'’]s\s+Discussion)",
        "next_pattern": r"(?:ITEM|Item)\s+7A[\.\:\s\-\_]+(?:Q\s*UANTITATIVE|Quantitative)",
    },
    {
        "id": "Item 7A",
        "name": "Market Risk",
        "pattern": r"(?:ITEM|Item)\s+7A[\.\:\s\-\_]+(?:Q\s*UANTITATIVE|Quantitative)",
        "next_pattern": r"(?:ITEM|Item)\s+8[\.\:\s\-\_]+(?:F\s*INANCIAL\s+STATEMENTS|Financial\s+Statements)",
    },
]


class SectionParser:
    """Extracts Item 1, Item 1A, Item 7 from 10-K filings, skipping TOC links."""

    def __init__(self, output_dir: str = "./data/processed/sections"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_sections(
        self,
        clean_text: str,
        ticker: str,
        fiscal_year: int,
        save_to_disk: bool = True,
        min_content_length: int = 100,
    ) -> Dict[str, Dict[str, Any]]:
        """Parse clean text and extract key sections."""
        results: Dict[str, Dict[str, Any]] = {}

        for sec in SECTIONS_CONFIG:
            sec_id = sec["id"]
            sec_name = sec["name"]
            pattern = sec["pattern"]
            next_pattern = sec["next_pattern"]

            # Find all start matches
            start_matches = list(re.finditer(pattern, clean_text, re.IGNORECASE))
            if not start_matches:
                logger.warning("Could not locate section %s in %s FY%d", sec_id, ticker, fiscal_year)
                continue

            # In SEC filings, the first match is usually Table of Contents.
            # Choose the occurrence that has substantial content after it.
            chosen_start = None
            chosen_end = None
            max_len = 0

            for sm in start_matches:
                start_idx = sm.end()
                # Search for next section pattern after start_idx
                next_match = re.search(next_pattern, clean_text[start_idx:], re.IGNORECASE)
                if next_match:
                    end_idx = start_idx + next_match.start()
                else:
                    end_idx = min(start_idx + 250000, len(clean_text))

                sec_content = clean_text[start_idx:end_idx].strip()
                # Check if it has substantial content
                if len(sec_content) > max_len and len(sec_content) >= min_content_length:
                    max_len = len(sec_content)
                    chosen_start = start_idx
                    chosen_end = end_idx

            if chosen_start is not None and chosen_end is not None:
                content = clean_text[chosen_start:chosen_end].strip()
                subsections = self._detect_subsections(sec_id, content)

                section_data = {
                    "ticker": ticker.upper(),
                    "fiscal_year": fiscal_year,
                    "section_id": sec_id,
                    "section_name": sec_name,
                    "length": len(content),
                    "subsections": subsections,
                    "content": content,
                }
                results[sec_id] = section_data

                if save_to_disk:
                    clean_id = sec_id.replace(" ", "").upper()
                    out_path = os.path.join(
                        self.output_dir,
                        f"{ticker.upper()}_{fiscal_year}_{clean_id}.json",
                    )
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(section_data, f, indent=2, ensure_ascii=False)
                    logger.info("Saved %s section %s (%d chars) to %s", ticker, sec_id, len(content), out_path)

        return results

    def _detect_subsections(self, section_id: str, content: str) -> List[Dict[str, Any]]:
        """Identify headings/subsections inside the section text, preserving paragraph boundaries."""
        subsections = []
        lines = content.split("\n")
        current_sub = "Overview"
        current_paras: List[str] = []
        current_lines: List[str] = []

        def flush_para():
            if current_lines:
                current_paras.append(" ".join(current_lines).strip())
                current_lines.clear()

        def flush_sub():
            flush_para()
            if current_paras:
                subsections.append({
                    "heading": current_sub,
                    "text": "\n\n".join(current_paras).strip()
                })
                current_paras.clear()

        for line in lines:
            line_str = line.strip()
            if not line_str:
                flush_para()
                continue

            # Heading patterns: markdown '#...', bold titles, or risk factors starting with bold text
            is_heading = False
            heading_title = ""

            if line_str.startswith("#"):
                is_heading = True
                heading_title = line_str.lstrip("#").strip()
            elif not line_str.startswith("|") and not line_str.startswith("---"):
                if section_id == "Item 1" and len(line_str) < 70 and not line_str.endswith("."):
                    if (line_str.isupper() and len(line_str) > 3) or line_str in (
                        "Company Background", "Products", "Services", "Segments",
                        "Markets and Distribution", "Competition", "Supply of Components",
                        "Research and Development", "Intellectual Property", "Human Capital",
                        "Available Information", "Operations", "Government Regulation",
                    ):
                        is_heading = True
                        heading_title = line_str
                elif section_id == "Item 1A" and len(line_str) < 140:
                    if (
                        line_str.startswith((
                            "Risks Related to", "Risks Concerning", "Macroeconomic",
                            "Business Risks", "Legal and Regulatory", "General Risks",
                            "Operational Risks", "Financial Risks",
                        ))
                        or (line_str.isupper() and len(line_str) > 5 and not line_str.endswith("."))
                        or (line_str.endswith(":") and len(line_str) < 100)
                    ):
                        is_heading = True
                        heading_title = line_str.rstrip(":")
                elif section_id in ("Item 7", "Item 7A") and len(line_str) < 80 and not line_str.endswith("."):
                    if not line_str.lower().startswith("and ") and any(
                        topic in line_str.lower() for topic in (
                            "results of operations", "overview", "liquidity and capital",
                            "critical accounting", "segment information", "segment operating",
                            "revenue", "gross margin", "research and development",
                            "operating expenses", "quantitative and qualitative", "market risk",
                        )
                    ):
                        is_heading = True
                        heading_title = line_str

            if is_heading and heading_title:
                flush_sub()
                current_sub = heading_title
            else:
                current_lines.append(line_str)

        flush_sub()
        return subsections
