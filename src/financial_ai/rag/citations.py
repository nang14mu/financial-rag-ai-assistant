"""Citation generator and validator for financial disclosures."""
import re
from typing import Dict, Any, List, Optional


def format_citation(metadata: Dict[str, Any]) -> str:
    """Format standard citation string from chunk metadata."""
    form = metadata.get("form_type", "10-K")
    ticker = metadata.get("ticker", "").upper()
    fy = metadata.get("fiscal_year", "")
    section = metadata.get("section", "")
    subsection = metadata.get("subsection") or metadata.get("heading", "")

    if subsection and subsection != section:
        return f"[Form {form}, {ticker}, FY{fy}, {section} - {subsection}]"
    return f"[Form {form}, {ticker}, FY{fy}, {section}]"


def parse_citations(text: str) -> List[Dict[str, str]]:
    """Extract citations from generated answers."""
    pattern = r"\[Form\s+([^,]+),\s*([A-Z]+),\s*FY(\d{4}),\s*([^\]]+)\]"
    matches = re.finditer(pattern, text)
    citations = []
    for m in matches:
        sec_sub = m.group(4).split(" - ", 1)
        section = sec_sub[0].strip()
        subsection = sec_sub[1].strip() if len(sec_sub) > 1 else ""
        citations.append({
            "full_citation": m.group(0),
            "form": m.group(1).strip(),
            "ticker": m.group(2).strip(),
            "fiscal_year": m.group(3).strip(),
            "section": section,
            "subsection": subsection,
        })
    return citations


# Alias for compatibility
parse_citation = parse_citations
