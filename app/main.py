"""Flask application – route handlers for the MakeHook service.

Endpoints
---------
GET  /health      → Liveness / readiness probe.
POST /v1/extract  → Accept raw text, return structured JSON.
"""

from __future__ import annotations

import hmac
import logging
import os
import time

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request

from app.extractor import extract

# ── Bootstrap ────────────────────────────────────────────────────────────────

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)

app = Flask(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _check_secret() -> str | None:
    """Return an error message if the shared secret header is missing/wrong.

    Uses constant-time comparison (hmac.compare_digest) to prevent timing attacks.
    When ``MAKEHOOK_SECRET`` is unset the check is skipped so local development stays frictionless.
    """
    expected = os.getenv("MAKEHOOK_SECRET")
    if not expected:
        return None  # secret not configured → allow all requests
    provided = request.headers.get("X-MakeHook-Secret", "")
    if not hmac.compare_digest(provided, expected):
        return "Invalid or missing X-MakeHook-Secret header."
    return None


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health() -> tuple[Response, int]:
    """Liveness probe – returns ``200`` when the service is up."""
    return jsonify({"status": "ok"}), 200


@app.route("/v1/extract", methods=["POST"])
def extract_endpoint() -> tuple[Response, int]:
    """Accept raw text and return structured extraction results.

    Expected request body::

        {
            "text": "Hi, I'm John Doe. My invoice #4412 is wrong …"
        }

    Returns ``200`` with the ``ExtractionResult`` JSON on success, or an
    appropriate ``4xx`` / ``5xx`` error payload.
    """
    # ── Auth ──────────────────────────────────────────────────────────────
    auth_error = _check_secret()
    if auth_error:
        log.warning("Unauthorized request from %s", request.remote_addr)
        return jsonify({"error": auth_error}), 401

    # ── Input validation ─────────────────────────────────────────────────
    body = request.get_json(silent=True)
    if not body or "text" not in body:
        return jsonify({"error": "Request body must contain a 'text' field."}), 400

    text: str = body["text"]
    if not text.strip():
        return jsonify({"error": "'text' field must not be empty."}), 400

    # ── Extraction ───────────────────────────────────────────────────────
    log.info("Extracting from %d-char input…", len(text))
    start = time.perf_counter()

    try:
        result = extract(text)
    except Exception:
        log.exception("Extraction failed")
        return jsonify({"error": "LLM extraction failed. Please try again later."}), 502

    elapsed_ms = (time.perf_counter() - start) * 1000
    log.info("Extraction completed in %.0f ms", elapsed_ms)

    return jsonify(result.model_dump(mode="json")), 200


# ── Development Server ───────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
