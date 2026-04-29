"""
Extract structured spending data from a receipt image or text using Claude.
"""

import anthropic
import base64
import os
import requests
from datetime import date


def _load_client() -> anthropic.Anthropic:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set in .env")
    return anthropic.Anthropic(api_key=key)


EXTRACTION_PROMPT = """You are a receipt parser. Extract spending data from the receipt and return ONLY valid JSON, no explanation.

Return this exact structure:
{{
  "merchant": "store or restaurant name",
  "date": "YYYY-MM-DD",
  "amount": 12.50,
  "currency": "NZD",
  "category": "one of: Food & Dining, Groceries, Transport, Entertainment, Shopping, Health & Medical, Utilities, Other",
  "notes": "brief description of what was purchased, or empty string"
}}

Rules:
- If date is not visible, use today's date: {today}
- amount must be a number (the total paid), not a string
- currency: guess from context or default to NZD
- category: pick the single best fit
- notes: 1 short sentence max, or empty string
"""


def from_image_url(image_url: str, twilio_auth: tuple[str, str]) -> dict:
    """Download an image from Twilio and extract receipt data."""
    client = _load_client()

    response = requests.get(image_url, auth=twilio_auth, timeout=30)
    response.raise_for_status()

    image_data = base64.standard_b64encode(response.content).decode("utf-8")
    content_type = response.headers.get("Content-Type", "image/jpeg")

    today = date.today().isoformat()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": content_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT.format(today=today),
                    },
                ],
            }
        ],
    )

    return _parse_response(message.content[0].text)


def from_text(text: str) -> dict:
    """Extract receipt data from a text description."""
    client = _load_client()

    today = date.today().isoformat()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": f"{EXTRACTION_PROMPT.format(today=today)}\n\nReceipt text:\n{text}",
            }
        ],
    )

    return _parse_response(message.content[0].text)


def _parse_response(raw: str) -> dict:
    import json
    import re

    raw = raw.strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in Claude response: {raw}")

    data = json.loads(match.group())
    required = {"merchant", "date", "amount", "currency", "category", "notes"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Missing fields in extraction: {missing}")

    data["amount"] = float(data["amount"])
    return data
