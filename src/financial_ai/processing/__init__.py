"""Processing package for SEC HTML cleaning, section parsing, chunking, and XBRL normalization."""
from financial_ai.processing.html_cleaner import clean_sec_html
from financial_ai.processing.section_parser import SectionParser
from financial_ai.processing.chunker import SemanticFinancialChunker
from financial_ai.processing.metric_mapper import MetricMapper
from financial_ai.processing.xbrl_normalizer import XBRLNormalizer

__all__ = [
    "clean_sec_html",
    "SectionParser",
    "SemanticFinancialChunker",
    "MetricMapper",
    "XBRLNormalizer",
]
