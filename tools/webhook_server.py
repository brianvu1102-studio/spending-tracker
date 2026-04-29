"""
Flask webhook server — receives WhatsApp messages from Twilio and logs receipts.

Run locally:
    python tools/webhook_server.py

Then expose with ngrok:
    ngrok http 5001

Set the ngrok HTTPS URL + /webhook as your Twilio Sandbox webhook URL.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

import tools.process_receipt as processor
import tools.sheets_manager as sheets


app = Flask(__name__)


def _validate_twilio_request() -> bool:
    """Validate that the request genuinely came from Twilio."""
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    validator = RequestValidator(auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = request.url
    params = request.form.to_dict()
    return validator.validate(url, params, signature)


def _twilio_auth() -> tuple[str, str]:
    return (
        os.environ.get("TWILIO_ACCOUNT_SID", ""),
        os.environ.get("TWILIO_AUTH_TOKEN", ""),
    )


def _reply(message: str) -> str:
    resp = MessagingResponse()
    resp.message(message)
    return str(resp)


@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.form.get("Body", "").strip()
    num_media = int(request.form.get("NumMedia", 0))
    sender = request.form.get("From", "")

    print(f"\n--- Incoming from {sender} ---")
    print(f"Text: {body!r} | Media: {num_media}")

    # Help command
    if body.lower() in {"help", "hi", "hello"}:
        return _reply(
            "Hi! Send me a photo of your receipt or describe your purchase "
            "(e.g. 'Starbucks $5.50') and I'll log it for you. "
            "Send 'summary' for this week's spending."
        )

    # Manual summary request
    if body.lower() in {"summary", "report", "spending"}:
        transactions = sheets.get_current_week_transactions()
        if not transactions:
            return _reply("No spending logged this week yet. Start sending receipts!")
        total = sum(t["amount"] for t in transactions)
        currency = transactions[0]["currency"] if transactions else "USD"
        lines = [f"This week so far: {currency} {total:.2f} across {len(transactions)} transactions."]
        from collections import defaultdict
        by_cat = defaultdict(float)
        for t in transactions:
            by_cat[t["category"]] += t["amount"]
        for cat, amt in sorted(by_cat.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat}: {currency} {amt:.2f}")
        return _reply("\n".join(lines))

    # Process receipt image
    if num_media > 0:
        media_url = request.form.get("MediaUrl0", "")
        content_type = request.form.get("MediaContentType0", "")

        if not content_type.startswith("image/"):
            return _reply("Please send an image of your receipt (JPEG or PNG).")

        try:
            transaction = processor.from_image_url(media_url, _twilio_auth())
        except Exception as e:
            print(f"Image processing error: {e}")
            return _reply(
                "Couldn't read that receipt. Try sending a clearer photo, "
                "or type the details (e.g. 'Grab $8.50 transport')."
            )

    # Process text description
    elif body:
        try:
            transaction = processor.from_text(body)
        except Exception as e:
            print(f"Text processing error: {e}")
            return _reply(
                "Couldn't parse that. Try something like: 'Lunch at McDonald's $12.50' "
                "or send a photo of the receipt."
            )
    else:
        return _reply("Send a receipt photo or describe your purchase to log it.")

    # Save to Google Sheets
    try:
        sheets.append_transaction(transaction)
    except Exception as e:
        print(f"Sheets error: {e}")
        return _reply("Logged locally but couldn't save to Google Sheets. Check the server logs.")

    print(f"Logged: {transaction}")

    confirmation = (
        f"Logged! {transaction['merchant']} — "
        f"{transaction['currency']} {transaction['amount']:.2f} "
        f"({transaction['category']}) on {transaction['date']}"
    )
    return _reply(confirmation)


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"
    print(f"Starting webhook server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
