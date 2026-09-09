"""Unit tests verifying mandatory LLM enforcement across all components."""
import os
import pytest
from unittest.mock import patch

from financial_ai.generation.llm import get_llm
from financial_ai.generation.answer_generator import FinancialAnswerGenerator
from financial_ai.text2sql.generator import Text2SQLGenerator


def test_get_llm_raises_when_no_keys():
    """Verify get_llm strictly raises RuntimeError if no API keys are configured."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "", "GEMINI_API_KEY": ""}, clear=False):
        with pytest.raises(RuntimeError, match="LLM is MANDATORY"):
            get_llm()


def test_get_llm_raises_when_dummy_keys():
    """Verify get_llm strictly raises RuntimeError when dummy key is provided."""
    with patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "dummy_key_for_testing", "GEMINI_API_KEY": "dummy_key_for_testing", "LLM_PROVIDER": "gemini"},
        clear=False,
    ):
        with pytest.raises(RuntimeError, match="LLM is MANDATORY"):
            get_llm()


def test_answer_generator_raises_when_no_llm():
    """Verify FinancialAnswerGenerator cannot instantiate without LLM."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "", "GEMINI_API_KEY": ""}, clear=False):
        with pytest.raises(RuntimeError, match="LLM is MANDATORY"):
            FinancialAnswerGenerator()


def test_text2sql_generator_raises_when_no_llm():
    """Verify Text2SQLGenerator cannot instantiate without LLM."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "", "GEMINI_API_KEY": ""}, clear=False):
        with pytest.raises(RuntimeError, match="LLM is MANDATORY"):
            Text2SQLGenerator()


def test_get_llm_initializes_with_valid_key():
    """Verify get_llm initializes ChatGoogleGenerativeAI with valid key."""
    with patch.dict(
        os.environ,
        {"GEMINI_API_KEY": "test_valid_key_12345", "LLM_PROVIDER": "gemini"},
        clear=False,
    ):
        llm = get_llm()
        assert llm is not None
        assert "Google" in llm.__class__.__name__ or "Gemini" in llm.__class__.__name__
