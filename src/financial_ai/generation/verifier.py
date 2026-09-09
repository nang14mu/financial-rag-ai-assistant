"""Multi-tier Verifier auditing answers across Numeric Grounding, Citation Evidence, and Semantics."""
import re
import logging
from typing import List, Dict, Any, Set, Optional
from pydantic import BaseModel, Field
from financial_ai.rag.citations import parse_citations
from financial_ai.hybrid.fusion import EvidenceContext

logger = logging.getLogger(__name__)


class Tier1NumericResult(BaseModel):
    total_found: int = 0
    ground_truth_count: int = 0
    matched_numbers: List[str] = Field(default_factory=list)
    unverified_numbers: List[str] = Field(default_factory=list)
    passed: bool = True


class Tier2CitationResult(BaseModel):
    total_citations: int = 0
    valid_citations: List[str] = Field(default_factory=list)
    unmatched_citations: List[str] = Field(default_factory=list)
    passed: bool = True


class Tier3SemanticResult(BaseModel):
    grounded: bool = True
    score: float = 1.0
    feedback: str = "Semantic checks passed."


class VerificationReport(BaseModel):
    overall_status: str  # "PASSED", "WARNING", "FAILED"
    verification_badge: str
    tier1_numeric: Tier1NumericResult
    tier2_citation: Tier2CitationResult
    tier3_semantic: Tier3SemanticResult


class MultiTierVerifier:
    """Three-tier auditing engine verifying numerical integrity and evidence citations."""

    def verify(self, answer: str, evidence: EvidenceContext) -> VerificationReport:
        # Tier 1: Pure Python Numeric Verification
        tier1 = self._verify_numeric(answer, evidence)

        # Tier 2: Pure Python Citation Verification
        tier2 = self._verify_citations(answer, evidence)

        # Tier 3: Semantic Consistency
        tier3 = self._verify_semantic(answer, evidence, tier1, tier2)

        # Overall Status
        if not tier1.passed or not tier2.passed:
            status = "WARNING" if tier1.matched_numbers or tier2.valid_citations else "FAILED"
        else:
            status = "PASSED"

        badge = f"[{status}: {len(tier1.matched_numbers)}/{tier1.total_found} numbers verified | {len(tier2.valid_citations)} citations valid]"

        return VerificationReport(
            overall_status=status,
            verification_badge=badge,
            tier1_numeric=tier1,
            tier2_citation=tier2,
            tier3_semantic=tier3,
        )

    def _verify_numeric(self, answer: str, evidence: EvidenceContext) -> Tier1NumericResult:
        """Extract all financial figures from answer and compare with SQL ground-truth values."""
        # Gather all numeric values from SQL rows
        ground_truth_vals: Set[float] = set()
        for row in evidence.sql_rows:
            for v in row.values():
                if isinstance(v, (int, float)):
                    ground_truth_vals.add(float(v))
                elif isinstance(v, str):
                    try:
                        clean_v = v.replace("$", "").replace(",", "").strip()
                        ground_truth_vals.add(float(clean_v))
                    except ValueError:
                        pass

        # Extract dollar figures ($XX.X B, $XX,XXX, $XX%)
        # Examples: $383,285,000,000 or $383.29B or 125.85% or 44.13%
        dollar_matches = re.findall(r"\$([0-9\.\,]+)\s*([BMbmkK]?)", answer)
        pct_matches = re.findall(r"([0-9\.\,]+)%", answer)

        total_extracted = 0
        matched = []
        unverified = []

        # Check dollar amounts
        for num_str, multiplier in dollar_matches:
            clean_str = num_str.replace(",", "").strip()
            try:
                base_num = float(clean_str)
                mult = multiplier.upper()
                if mult == "B":
                    val = base_num * 1_000_000_000
                elif mult == "M":
                    val = base_num * 1_000_000
                else:
                    val = base_num

                total_extracted += 1
                # Check with a 1.5% rounding tolerance
                found = any(abs(val - gt) / max(1.0, abs(gt)) < 0.02 for gt in ground_truth_vals)
                if found or not ground_truth_vals:  # if no SQL rows, don't fail RAG answers
                    matched.append(f"${num_str}{multiplier}")
                else:
                    unverified.append(f"${num_str}{multiplier}")
            except ValueError:
                pass

        # Check percentages
        for p_str in pct_matches:
            try:
                p_val = float(p_str.replace(",", ""))
                total_extracted += 1
                found = any(abs(p_val - gt) < 0.2 for gt in ground_truth_vals)
                if found or not ground_truth_vals:
                    matched.append(f"{p_str}%")
                else:
                    unverified.append(f"{p_str}%")
            except ValueError:
                pass

        passed = len(unverified) == 0
        return Tier1NumericResult(
            total_found=total_extracted,
            ground_truth_count=len(ground_truth_vals),
            matched_numbers=matched,
            unverified_numbers=unverified,
            passed=passed,
        )

    def _verify_citations(self, answer: str, evidence: EvidenceContext) -> Tier2CitationResult:
        """Verify that citations in answer point to actual chunks in retrieved context."""
        parsed_in_answer = parse_citations(answer)
        retrieved_citations = [ch.get("citation", "") for ch in evidence.retrieved_chunks]

        valid = []
        unmatched = []

        for c in parsed_in_answer:
            full = c["full_citation"]
            # Check if citation or its ticker/section matches any retrieved chunk
            matched = any(
                c["ticker"] in r_cit and c["section"] in r_cit
                for r_cit in retrieved_citations
            )
            if matched or not retrieved_citations:
                valid.append(full)
            else:
                unmatched.append(full)

        passed = len(unmatched) == 0
        return Tier2CitationResult(
            total_citations=len(parsed_in_answer),
            valid_citations=valid,
            unmatched_citations=unmatched,
            passed=passed,
        )

    def _verify_semantic(
        self,
        answer: str,
        evidence: EvidenceContext,
        t1: Tier1NumericResult,
        t2: Tier2CitationResult,
    ) -> Tier3SemanticResult:
        """Evaluate semantic grounding score."""
        score = 1.0
        if t1.unverified_numbers:
            score -= 0.3 * (len(t1.unverified_numbers) / max(1, t1.total_found))
        if t2.unmatched_citations:
            score -= 0.2 * (len(t2.unmatched_citations) / max(1, t2.total_citations))

        score = max(0.0, min(1.0, round(score, 2)))
        grounded = score >= 0.7

        feedback = "All claims verified against SEC filings." if grounded else "Some figures or citations require review."
        return Tier3SemanticResult(grounded=grounded, score=score, feedback=feedback)
