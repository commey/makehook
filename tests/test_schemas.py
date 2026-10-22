"""Unit tests for Pydantic v2 schemas and validation bounds."""

import pytest
from app.schemas import ActionItem, Category, ExtractionResult, Urgency
from pydantic import ValidationError


def test_valid_extraction_result():
    """Test instantiating a valid ExtractionResult."""
    data = {
        "customer_name": "Marcus Aurelius",
        "category": "feedback",
        "urgency": "low",
        "summary": "Customer shared philosophical feedback on the user interface improvements.",
        "action_items": [
            {"description": "Log feedback in product tracker", "assignee": "Product"}
        ],
        "sentiment_score": 0.8,
    }
    result = ExtractionResult(**data)
    assert result.customer_name == "Marcus Aurelius"
    assert result.category == Category.FEEDBACK
    assert result.urgency == Urgency.LOW
    assert result.sentiment_score == 0.8
    assert len(result.action_items) == 1
    assert result.action_items[0].description == "Log feedback in product tracker"


@pytest.mark.parametrize("invalid_sentiment", [-1.5, 1.01, 5.0])
def test_sentiment_score_out_of_bounds(invalid_sentiment):
    """Sentiment score must be between -1.0 and 1.0."""
    data = {
        "category": "support",
        "urgency": "medium",
        "summary": "This is a valid summary of the message received.",
        "sentiment_score": invalid_sentiment,
    }
    with pytest.raises(ValidationError):
        ExtractionResult(**data)


def test_summary_too_short():
    """Summary with fewer than 10 characters should fail validation."""
    data = {
        "category": "support",
        "urgency": "low",
        "summary": "Short",
        "sentiment_score": 0.0,
    }
    with pytest.raises(ValidationError):
        ExtractionResult(**data)


def test_invalid_category_enum():
    """Non-existent category should fail validation."""
    data = {
        "category": "unsupported_category",
        "urgency": "low",
        "summary": "This is a valid summary of the issue.",
        "sentiment_score": 0.0,
    }
    with pytest.raises(ValidationError):
        ExtractionResult(**data)
