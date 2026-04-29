"""
Send WhatsApp messages via Twilio.
"""

import os
from twilio.rest import Client


def _get_client() -> Client:
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        raise EnvironmentError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in .env")
    return Client(account_sid, auth_token)


def send_message(to: str, body: str) -> str:
    """
    Send a WhatsApp message. Returns the message SID.

    to: recipient number in E.164 format, e.g. '+14155238886'
    """
    client = _get_client()
    from_number = os.environ.get("TWILIO_WHATSAPP_FROM")
    if not from_number:
        raise EnvironmentError("TWILIO_WHATSAPP_FROM must be set in .env (e.g. 'whatsapp:+14155238886')")

    if not from_number.startswith("whatsapp:"):
        from_number = f"whatsapp:{from_number}"
    if not to.startswith("whatsapp:"):
        to = f"whatsapp:{to}"

    message = client.messages.create(body=body, from_=from_number, to=to)
    return message.sid


def send_to_owner(body: str) -> str:
    """Send a message to the bot owner (configured in .env)."""
    owner = os.environ.get("OWNER_WHATSAPP_NUMBER")
    if not owner:
        raise EnvironmentError("OWNER_WHATSAPP_NUMBER must be set in .env (your WhatsApp number)")
    return send_message(owner, body)
