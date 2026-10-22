"""LLM extraction engine powered by Instructor.

This module wraps an OpenAI-compatible client with *Instructor* so every call
returns a validated ``ExtractionResult`` Pydantic model.  Automatic retries are
enabled – if the LLM produces output that fails schema validation, Instructor
re-prompts the model with the validation errors until a conforming response is
obtained (up to ``max_retries``).
"""

from __future__ import annotations

import os
from functools import lru_cache

import instructor
from openai import OpenAI

from app.schemas import ExtractionResult

# ── Constants ────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are an expert data-extraction assistant. "
    "Analyse the user-provided text and extract structured insights. "
    "Respond ONLY with the requested JSON schema – no commentary."
)

_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_MAX_RETRIES = 3


# ── Client Factory ───────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_client() -> instructor.Instructor:
    """Build and cache an Instructor-patched OpenAI client.

    The client reads ``OPENAI_API_KEY`` (and optionally ``OPENAI_BASE_URL``)
    from the environment, making it compatible with both OpenAI and any
    OpenAI-compatible provider (e.g. LiteLLM proxy, Azure, Ollama).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is missing. "
            "Please check your .env configuration."
        )
    base_url = os.getenv("OPENAI_BASE_URL")
    openai_client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    return instructor.from_openai(openai_client)


# ── Public API ───────────────────────────────────────────────────────────────

def extract(
    text: str,
    *,
    model: str | None = None,
    max_retries: int = _DEFAULT_MAX_RETRIES,
) -> ExtractionResult:
    """Extract structured insights from free-form *text*.

    Parameters
    ----------
    text:
        Raw, unstructured input (e.g. a customer email or support ticket).
    model:
        OpenAI model identifier.  Falls back to ``LLM_MODEL`` env var, then
        to ``gpt-4o-mini``.
    max_retries:
        How many times Instructor may re-prompt on validation failure.

    Returns
    -------
    ExtractionResult
        A fully validated Pydantic model instance.

    Raises
    ------
    instructor.exceptions.InstructorRetryException
        When the LLM still fails validation after *max_retries* attempts.
    openai.APIError
        On upstream API communication failures.
    """
    client = _get_client()
    resolved_model = model or os.getenv("LLM_MODEL", _DEFAULT_MODEL)

    return client.chat.completions.create(
        model=resolved_model,
        response_model=ExtractionResult,
        max_retries=max_retries,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )
