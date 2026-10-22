"""Unit and integration tests for MakeHook endpoints and extractor."""

from unittest.mock import MagicMock, patch

import pytest
from app.main import app
from app.schemas import ActionItem, Category, ExtractionResult, Urgency


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_extraction_result():
    return ExtractionResult(
        customer_name="Jane Doe",
        category=Category.BILLING,
        urgency=Urgency.HIGH,
        summary="Customer reported unexpected double charges on their subscription invoice.",
        action_items=[
            ActionItem(description="Review billing history and refund duplicate charge", assignee="Billing Support")
        ],
        sentiment_score=-0.65,
    )


def test_health_check(client):
    """GET /health returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_extract_missing_body(client):
    """POST /v1/extract without body returns 400."""
    response = client.post("/v1/extract", json=None)
    assert response.status_code == 400
    assert "text" in response.get_json()["error"]


def test_extract_empty_text(client):
    """POST /v1/extract with empty text returns 400."""
    response = client.post("/v1/extract", json={"text": "   "})
    assert response.status_code == 400
    assert "must not be empty" in response.get_json()["error"]


def test_extract_auth_failure(client, monkeypatch):
    """POST /v1/extract with invalid or missing secret header returns 401."""
    monkeypatch.setenv("MAKEHOOK_SECRET", "super-secret-token")

    # Missing header
    res1 = client.post("/v1/extract", json={"text": "Hello world"})
    assert res1.status_code == 401

    # Wrong header
    res2 = client.post(
        "/v1/extract",
        json={"text": "Hello world"},
        headers={"X-MakeHook-Secret": "wrong-token"},
    )
    assert res2.status_code == 401


@patch("app.main.extract")
def test_extract_success(mock_extract, client, mock_extraction_result, monkeypatch):
    """POST /v1/extract returns structured JSON when authenticated and valid."""
    monkeypatch.setenv("MAKEHOOK_SECRET", "super-secret-token")
    mock_extract.return_value = mock_extraction_result

    payload = {"text": "Hi, I am Jane Doe. I noticed a double charge on my account this morning."}
    response = client.post(
        "/v1/extract",
        json=payload,
        headers={"X-MakeHook-Secret": "super-secret-token"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["customer_name"] == "Jane Doe"
    assert data["category"] == "billing"
    assert data["urgency"] == "high"
    assert data["sentiment_score"] == -0.65
    assert len(data["action_items"]) == 1
    assert data["action_items"][0]["assignee"] == "Billing Support"
    mock_extract.assert_called_once_with(payload["text"])


@patch("app.main.extract")
def test_extract_llm_failure(mock_extract, client):
    """POST /v1/extract returns 502 when downstream LLM fails."""
    mock_extract.side_effect = RuntimeError("OpenAI API rate limit exceeded")

    response = client.post("/v1/extract", json={"text": "Please assist me with my login issue."})
    assert response.status_code == 502
    assert "LLM extraction failed" in response.get_json()["error"]
