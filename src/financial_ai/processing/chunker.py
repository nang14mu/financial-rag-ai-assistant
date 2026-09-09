"""Semantic Financial Chunker adhering to SEC 10-K domain boundaries and exact token rules."""
import os
import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
    def count_tokens(text: str) -> int:
        return len(_enc.encode(text))
except Exception:
    def count_tokens(text: str) -> int:
        # Fallback estimation: ~4 chars per token
        return max(1, len(text) // 4)

logger = logging.getLogger(__name__)


class SemanticFinancialChunker:
    """Chunks 10-K sections by subsection, heading, and paragraph with Parent-Child hierarchical support."""

    def __init__(
        self,
        subsection_threshold: int = 1500,
        chunk_min_tokens: int = 800,
        chunk_max_tokens: int = 1500,
        overlap_tokens: int = 60,
        child_chunk_tokens: int = 180,
        child_overlap_tokens: int = 35,
        output_dir: str = "./data/processed/chunks",
    ):
        self.subsection_threshold = subsection_threshold
        self.chunk_min_tokens = chunk_min_tokens
        self.chunk_max_tokens = chunk_max_tokens
        self.overlap_tokens = overlap_tokens
        self.child_chunk_tokens = child_chunk_tokens
        self.child_overlap_tokens = child_overlap_tokens
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text cleanly into sentences using punctuation boundaries."""
        sentences = re.split(r'(?<=[.?!])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_text_by_sentences(self, text: str, max_tokens: int) -> List[str]:
        """Fallback to split an oversized paragraph into smaller sentence blocks <= max_tokens."""
        sentences = self._split_into_sentences(text)
        if not sentences:
            sentences = [text]

        blocks: List[str] = []
        curr: List[str] = []
        curr_tokens = 0

        for s in sentences:
            s_tok = count_tokens(s)
            # If a single sentence exceeds max_tokens, slice it by words
            if s_tok > max_tokens:
                if curr:
                    blocks.append(" ".join(curr))
                    curr = []
                    curr_tokens = 0
                words = s.split()
                sub_w: List[str] = []
                sub_tok = 0
                for w in words:
                    wt = count_tokens(w + " ")
                    if sub_tok + wt > max_tokens and sub_w:
                        blocks.append(" ".join(sub_w))
                        sub_w = [w]
                        sub_tok = wt
                    else:
                        sub_w.append(w)
                        sub_tok += wt
                if sub_w:
                    blocks.append(" ".join(sub_w))
                continue

            if curr_tokens + s_tok > max_tokens and curr:
                blocks.append(" ".join(curr))
                curr = [s]
                curr_tokens = s_tok
            else:
                curr.append(s)
                curr_tokens += s_tok

        if curr:
            blocks.append(" ".join(curr))

        return blocks

    def chunk_section(
        self,
        ticker: str,
        fiscal_year: int,
        section_id: str,
        section_name: str,
        subsections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Chunk a parsed section into Parent Chunks according to financial domain rules."""
        chunks: List[Dict[str, Any]] = []
        chunk_index = 1
        clean_sec_code = section_id.replace(" ", "").upper()

        for sub in subsections:
            heading = sub.get("heading", "General")
            text = sub.get("text", "").strip()
            if not text:
                continue

            sub_tokens = count_tokens(text)

            # Rule 1: If subsection <= subsection_threshold (1500 tokens), keep intact as 1 chunk
            if sub_tokens <= self.subsection_threshold:
                chunk_id = f"{ticker}_{fiscal_year}_{clean_sec_code}_{chunk_index:03d}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": f"### {heading}\n\n{text}",
                    "token_count": sub_tokens,
                    "metadata": {
                        "ticker": ticker.upper(),
                        "fiscal_year": fiscal_year,
                        "form_type": "10-K",
                        "section": section_id,
                        "section_name": section_name,
                        "subsection": heading,
                        "heading": heading,
                        "chunk_id": chunk_id,
                        "parent_id": chunk_id,
                    }
                })
                chunk_index += 1
                continue

            # Rule 2: Subsection > threshold -> split into chunks of chunk_max_tokens
            # Split into paragraphs to preserve paragraph boundaries
            raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

            # Handle edge cases where a single paragraph is too large
            paragraphs: List[str] = []
            for p in raw_paragraphs:
                if count_tokens(p) > self.chunk_max_tokens:
                    paragraphs.extend(self._split_text_by_sentences(p, self.chunk_max_tokens))
                else:
                    paragraphs.append(p)

            current_paras: List[str] = []
            current_tokens = 0

            for p in paragraphs:
                p_tokens = count_tokens(p)

                # If adding this paragraph exceeds chunk_max_tokens and we already have content
                if current_tokens + p_tokens > self.chunk_max_tokens and current_paras:
                    chunk_text = f"### {heading}\n\n" + "\n\n".join(current_paras)
                    chunk_id = f"{ticker}_{fiscal_year}_{clean_sec_code}_{chunk_index:03d}"
                    chunks.append({
                        "chunk_id": chunk_id,
                        "text": chunk_text,
                        "token_count": count_tokens(chunk_text),
                        "metadata": {
                            "ticker": ticker.upper(),
                            "fiscal_year": fiscal_year,
                            "form_type": "10-K",
                            "section": section_id,
                            "section_name": section_name,
                            "subsection": heading,
                            "heading": heading,
                            "chunk_id": chunk_id,
                            "parent_id": chunk_id,
                        }
                    })
                    chunk_index += 1

                    # Paragraph overlap: Keep the last paragraph for context if reasonable
                    if len(current_paras) > 1 and count_tokens(current_paras[-1]) <= self.overlap_tokens * 2:
                        current_paras = [current_paras[-1], p]
                        current_tokens = count_tokens(current_paras[0]) + p_tokens
                    else:
                        current_paras = [p]
                        current_tokens = p_tokens
                else:
                    current_paras.append(p)
                    current_tokens += p_tokens

            # Flush remaining paragraphs
            if current_paras:
                chunk_text = f"### {heading}\n\n" + "\n\n".join(current_paras)
                chunk_id = f"{ticker}_{fiscal_year}_{clean_sec_code}_{chunk_index:03d}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "token_count": count_tokens(chunk_text),
                    "metadata": {
                        "ticker": ticker.upper(),
                        "fiscal_year": fiscal_year,
                        "form_type": "10-K",
                        "section": section_id,
                        "section_name": section_name,
                        "subsection": heading,
                        "heading": heading,
                        "chunk_id": chunk_id,
                        "parent_id": chunk_id,
                    }
                })
                chunk_index += 1

        logger.info(
            "Created %d semantic parent chunks for %s FY%d %s",
            len(chunks),
            ticker,
            fiscal_year,
            section_id,
        )
        return chunks

    def create_child_chunks(self, parent_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Slice Parent Chunks into granular Child Chunks (150-200 tokens) for dense vector search."""
        all_children: List[Dict[str, Any]] = []

        for parent in parent_chunks:
            parent_id = parent["chunk_id"]
            parent_text = parent["text"]
            parent_meta = parent["metadata"]
            heading = parent_meta.get("heading", "General")

            # Split parent text into sentences
            # Note: strip off markdown heading if present for cleaner child sentence splitting
            content_to_split = parent_text
            if content_to_split.startswith(f"### {heading}\n\n"):
                content_to_split = content_to_split[len(f"### {heading}\n\n"):]

            sentences = self._split_into_sentences(content_to_split)
            if not sentences:
                sentences = [content_to_split]

            curr_sentences: List[str] = []
            curr_tokens = 0
            child_idx = 1

            for s in sentences:
                s_tok = count_tokens(s)
                # If a single sentence exceeds child_chunk_tokens, slice it
                if s_tok > self.child_chunk_tokens:
                    sub_blocks = self._split_text_by_sentences(s, self.child_chunk_tokens)
                    for sb in sub_blocks:
                        sb_tok = count_tokens(sb)
                        if curr_tokens + sb_tok > self.child_chunk_tokens and curr_sentences:
                            child_text = f"[{heading}] " + " ".join(curr_sentences)
                            child_id = f"{parent_id}_c{child_idx:02d}"
                            child_meta = dict(parent_meta)
                            child_meta.update({
                                "chunk_id": child_id,
                                "parent_id": parent_id,
                                "is_child": True,
                                "child_index": child_idx,
                            })
                            all_children.append({
                                "chunk_id": child_id,
                                "parent_id": parent_id,
                                "text": child_text,
                                "token_count": count_tokens(child_text),
                                "metadata": child_meta,
                            })
                            child_idx += 1
                            curr_sentences = [sb]
                            curr_tokens = sb_tok
                        else:
                            curr_sentences.append(sb)
                            curr_tokens += sb_tok
                    continue

                if curr_tokens + s_tok > self.child_chunk_tokens and curr_sentences:
                    child_text = f"[{heading}] " + " ".join(curr_sentences)
                    child_id = f"{parent_id}_c{child_idx:02d}"
                    child_meta = dict(parent_meta)
                    child_meta.update({
                        "chunk_id": child_id,
                        "parent_id": parent_id,
                        "is_child": True,
                        "child_index": child_idx,
                    })
                    all_children.append({
                        "chunk_id": child_id,
                        "parent_id": parent_id,
                        "text": child_text,
                        "token_count": count_tokens(child_text),
                        "metadata": child_meta,
                    })
                    child_idx += 1

                    # Sentence overlap
                    overlap_sents: List[str] = []
                    ot = 0
                    for osent in reversed(curr_sentences):
                        st = count_tokens(osent)
                        if ot + st <= self.child_overlap_tokens:
                            overlap_sents.insert(0, osent)
                            ot += st
                        else:
                            break
                    curr_sentences = overlap_sents + [s]
                    curr_tokens = sum(count_tokens(x) for x in curr_sentences)
                else:
                    curr_sentences.append(s)
                    curr_tokens += s_tok

            # Flush remaining child sentences
            if curr_sentences:
                child_text = f"[{heading}] " + " ".join(curr_sentences)
                child_id = f"{parent_id}_c{child_idx:02d}"
                child_meta = dict(parent_meta)
                child_meta.update({
                    "chunk_id": child_id,
                    "parent_id": parent_id,
                    "is_child": True,
                    "child_index": child_idx,
                })
                all_children.append({
                    "chunk_id": child_id,
                    "parent_id": parent_id,
                    "text": child_text,
                    "token_count": count_tokens(child_text),
                    "metadata": child_meta,
                })

        logger.info(
            "Created %d child chunks across %d parent chunks",
            len(all_children),
            len(parent_chunks),
        )
        return all_children

    def chunk_hierarchical(
        self,
        ticker: str,
        fiscal_year: int,
        section_id: str,
        section_name: str,
        subsections: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Perform full hierarchical chunking returning both Parent and Child chunks."""
        parents = self.chunk_section(
            ticker=ticker,
            fiscal_year=fiscal_year,
            section_id=section_id,
            section_name=section_name,
            subsections=subsections,
        )
        children = self.create_child_chunks(parents)
        return {"parents": parents, "children": children}

    def save_chunks(
        self,
        chunks: List[Dict[str, Any]],
        ticker: str,
        fiscal_year: int,
        suffix: str = "chunks",
    ) -> str:
        """Save chunk list to jsonl in data/processed/chunks/."""
        filename = f"{ticker}_{fiscal_year}_{suffix}.jsonl"
        out_path = os.path.join(self.output_dir, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            for ch in chunks:
                f.write(json.dumps(ch, ensure_ascii=False) + "\n")
        logger.info("Saved %d chunks to %s", len(chunks), out_path)
        return out_path

    def save_hierarchical_chunks(
        self,
        parents: List[Dict[str, Any]],
        children: List[Dict[str, Any]],
        ticker: str,
        fiscal_year: int,
    ) -> Tuple[str, str]:
        """Save both Parent Chunks and Child Chunks to respective jsonl files."""
        parent_path = self.save_chunks(parents, ticker, fiscal_year, suffix="parents")
        child_path = self.save_chunks(children, ticker, fiscal_year, suffix="children")
        return parent_path, child_path
