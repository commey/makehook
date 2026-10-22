"""Pydantic v2 schemas for structured LLM extraction.

Every field is strictly typed so that *Instructor* can guarantee the LLM output
conforms to the contract Make.com expects.
"""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class Urgency(str, Enum):
    """Urgency level assigned to the incoming message."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Category(str, Enum):
    """High-level category the message falls into."""

    SUPPORT = "support"
    SALES = "sales"
    BILLING = "billing"
    FEEDBACK = "feedback"
    GENERAL = "general"
    OTHER = "other"


class ActionItem(BaseModel):
    """A single follow-up action extracted from the text."""

    description: str = Field(
        ...,
        min_length=1,
        description="Concise description of the action to take.",
    )
    assignee: str | None = Field(
        default=None,
        description="Person or team responsible, if mentioned.",
    )


class ExtractionResult(BaseModel):
    """Structured insight payload returned by the extraction endpoint.

    Instructor uses this schema as the *response_model* so the LLM is forced to
    produce output that validates against every constraint defined here.
    """

    customer_name: str | None = Field(
        default=None,
        description="Full name of the customer, if identifiable.",
    )
    category: Category = Field(
        ...,
        description="Primary category of the message.",
    )
    urgency: Urgency = Field(
        ...,
        description="How urgent the message is.",
    )
    summary: str = Field(
        ...,
        min_length=10,
        max_length=300,
        description="Brief, neutral summary of the message content.",
    )
    action_items: List[ActionItem] = Field(
        default_factory=list,
        description="Concrete next steps derived from the message.",
    )
    sentiment_score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Sentiment from -1.0 (very negative) to 1.0 (very positive).",
    )
