"""Financial Answer Generator synthesizing professional reports with multi-tier verification."""
import os
import logging
from typing import Dict, Any, Optional
from financial_ai.generation.llm import get_llm, extract_llm_text
from financial_ai.hybrid.fusion import EvidenceContext
from financial_ai.generation.verifier import MultiTierVerifier, VerificationReport

logger = logging.getLogger(__name__)


class FinancialAnswerGenerator:
    """Generates structured financial analysis reports and verifies claims against ground truth using mandatory LLM."""

    def __init__(self, verifier: Optional[MultiTierVerifier] = None, llm: Optional[Any] = None):
        self.verifier = verifier or MultiTierVerifier()
        self.llm = llm or get_llm(temperature=0.1)

    def generate(self, evidence: EvidenceContext) -> Dict[str, Any]:
        """Synthesize report via LLM and run 3-tier verifier.
        
        Raises:
            RuntimeError: If LLM is not initialized or LLM generation fails.
        """
        if not self.llm:
            raise RuntimeError("FinancialAnswerGenerator requires an active LLM. No LLM instance available.")

        try:
            answer = self._llm_generate(evidence)
        except Exception as exc:
            logger.error("Mandatory LLM generation failed: %s", exc)
            raise RuntimeError(f"LLM generation failed: {exc}") from exc

        # Run 3-Tier Verification
        report: VerificationReport = self.verifier.verify(answer, evidence)

        return {
            "answer": answer,
            "verification": report.model_dump(),
            "evidence": evidence.model_dump(),
        }

    def _llm_generate(self, evidence: EvidenceContext) -> str:
        prompt = (
            "You are a Senior Wall Street Equity Research Analyst.\n"
            "Based ONLY on the provided verified evidence context below, answer the user query.\n\n"
            f"Evidence Context:\n{evidence.to_prompt_context()}\n\n"
            f"User Query: {evidence.user_query}\n\n"
            "Guidelines:\n"
            "- Answer in the same language as the user query (Vietnamese or English).\n"
            "- Present numbers in clear Markdown tables or bullet points.\n"
            "- Cite sources exactly using [Form 10-K, {TICKER}, FY{YEAR}, {SECTION} - {SUBSECTION}].\n"
            "- Do not extrapolate numbers not present in the evidence.\n"
        )
        resp = self.llm.invoke(prompt)
        return extract_llm_text(resp)
