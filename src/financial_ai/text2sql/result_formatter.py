"""Formats SQL query results into Markdown tables and structured summaries."""
from typing import List, Dict, Any


def format_sql_result(rows: List[Dict[str, Any]]) -> str:
    """Format query output rows into a clean Markdown table."""
    if not rows:
        return "No records found matching query criteria."

    headers = list(rows[0].keys())
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"

    row_lines = []
    for row in rows:
        formatted_vals = []
        for h in headers:
            v = row.get(h)
            if v is None:
                formatted_vals.append("N/A")
            elif isinstance(v, float) or isinstance(v, int):
                # Format large financial figures nicely
                if abs(v) >= 1_000_000:
                    formatted_vals.append(f"${v:,.2f}")
                else:
                    formatted_vals.append(str(v))
            else:
                formatted_vals.append(str(v))
        row_lines.append("| " + " | ".join(formatted_vals) + " |")

    return "\n".join([header_line, separator_line] + row_lines)
