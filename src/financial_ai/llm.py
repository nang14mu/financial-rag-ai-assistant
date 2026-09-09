"""Centralized LLM Factory enforcing mandatory LLM configuration."""
import os
import logging
from typing import Any
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def extract_llm_text(resp: Any) -> str:
    """Extract clean string text from LangChain LLM response across different providers/SDK versions."""
    content = getattr(resp, "content", resp)
    if isinstance(content, str):
        return content.strip()
    elif isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            elif isinstance(item, str):
                parts.append(item)
            elif hasattr(item, "text"):
                parts.append(str(getattr(item, "text")))
            else:
                parts.append(str(item))
        return "\n".join(parts).strip()
    return str(content).strip()


def get_llm(temperature: float = 0.0) -> Any:
    """Retrieve and initialize the configured LLM.
    
    Raises:
        RuntimeError: If no valid LLM configuration or API key is provided.
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    # Determine provider if ambiguous
    if provider == "openai":
        if not openai_key or openai_key == "dummy_key_for_testing":
            # If OpenAI was selected but no OpenAI key and Gemini key exists, switch to Gemini
            if gemini_key and gemini_key != "dummy_key_for_testing":
                provider = "gemini"
            else:
                raise RuntimeError(
                    "LLM is MANDATORY. Provider is set to 'openai', but OPENAI_API_KEY is missing or invalid. "
                    "Please configure a valid OPENAI_API_KEY or set LLM_PROVIDER=gemini in .env."
                )

    if provider == "gemini":
        if not gemini_key or gemini_key == "dummy_key_for_testing":
            raise RuntimeError(
                "LLM is MANDATORY. Provider is set to 'gemini', but GEMINI_API_KEY is missing or invalid. "
                "Please configure a valid GEMINI_API_KEY in .env."
            )
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            model_name = os.getenv("LLM_MODEL", "gemini-3.6-flash")
            if not model_name or "gpt" in model_name or "1.5" in model_name or "2.5" in model_name:
                model_name = "gemini-3.6-flash"
            logger.info("Initializing ChatGoogleGenerativeAI (model=%s, temp=%s)", model_name, temperature)
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=gemini_key,
                temperature=temperature,
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize Gemini LLM: {exc}") from exc

    elif provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
            model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
            logger.info("Initializing ChatOpenAI (model=%s, temp=%s)", model_name, temperature)
            return ChatOpenAI(
                model=model_name,
                api_key=openai_key,
                temperature=temperature,
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize OpenAI LLM: {exc}") from exc

    else:
        raise RuntimeError(
            f"Unsupported LLM_PROVIDER '{provider}'. Supported options are 'gemini' or 'openai'."
        )
