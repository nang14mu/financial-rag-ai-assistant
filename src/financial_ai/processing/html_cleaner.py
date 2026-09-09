"""Cleans SEC EDGAR 10-K HTML documents by stripping boilerplate, scripts, and inline XBRL artifacts."""
import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def clean_sec_html(html_content: str) -> str:
    """Clean raw SEC 10-K HTML and return readable markdown-style text preserving structure."""
    if not html_content or not html_content.strip():
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove all script, style, header, noscript, svg, metadata tags
    for tag in soup(["script", "style", "noscript", "svg", "ix:header", "head"]):
        tag.decompose()

    # Unwrap inline formatting and inline XBRL tags so words aren't split (e.g. B USINESS)
    for tag in soup.find_all(["span", "font", "b", "i", "u", "strong", "em", "ix:nonnumeric", "ix:nonfraction"]):
        tag.unwrap()

    # Convert HTML tables to Markdown tables to preserve financial disclosures
    for table in soup.find_all("table"):
        md_rows = []
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            col_texts = [re.sub(r"\s+", " ", col.get_text(strip=True)) for col in cols]
            # Keep rows with meaningful content
            if any(col_texts):
                md_rows.append("| " + " | ".join(col_texts) + " |")

        if md_rows:
            # Create header separator if at least one row exists
            header_sep = "| " + " | ".join(["---"] * len(rows[0].find_all(["td", "th"]))) + " |"
            if len(md_rows) > 1:
                md_rows.insert(1, header_sep)
            table.replace_with("\n\n" + "\n".join(md_rows) + "\n\n")
        else:
            table.decompose()

    # Convert headings
    for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        h_text = re.sub(r"\s+", " ", h.get_text(strip=True))
        if h_text:
            level = int(h.name[1])
            prefix = "#" * level
            h.replace_with(f"\n\n{prefix} {h_text}\n\n")

    # Convert paragraphs and divs
    for p in soup.find_all(["p", "div"]):
        p_text = p.get_text(separator=" ", strip=True)
        if p_text:
            p.replace_with(f"\n\n{p_text}\n\n")

    text = soup.get_text(separator="\n")

    # Normalize excessive newlines and whitespace
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    # Remove SEC page number lines (e.g. "Table of Contents", "- 45 -", "Page 12")
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if re.match(r"^-\s*\d+\s*-$", stripped) or re.match(r"^Page\s+\d+$", stripped, re.IGNORECASE):
            continue
        lines.append(line)

    cleaned = "\n".join(lines).strip()
    return cleaned
