"""
Generate a weekly spending summary using Claude and send it via WhatsApp.
Run this script every Sunday evening (or Monday morning) via cron.

Usage:
    python tools/weekly_summary.py
    python tools/weekly_summary.py --month   # monthly summary instead
"""

import anthropic
import os
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import tools.sheets_manager as sheets
import tools.whatsapp_sender as wa


WEEKLY_PROMPT = """You are a friendly personal finance assistant.
Summarize the user's spending data for this week in a WhatsApp message.

Spending data (JSON):
{data}

Guidelines:
- Keep it concise — WhatsApp, not a report
- Start with a warm greeting and the total spent
- Show a breakdown by category (sorted by amount, highest first)
- Call out the single biggest expense
- Give one practical, encouraging tip based on their spending pattern
- Use simple emoji sparingly (2-3 max) to make it readable
- End with a motivational one-liner about their finances
- Do NOT use markdown headers or bullet formatting — plain text only
- Keep the whole message under 300 words
"""


def _build_data_summary(transactions: list[dict]) -> dict:
    if not transactions:
        return {"total": 0, "count": 0, "by_category": {}, "transactions": []}

    by_category = defaultdict(float)
    for tx in transactions:
        by_category[tx["category"]] += tx["amount"]

    total = sum(tx["amount"] for tx in transactions)
    biggest = max(transactions, key=lambda t: t["amount"])

    return {
        "total": round(total, 2),
        "count": len(transactions),
        "currency": transactions[0]["currency"] if transactions else "USD",
        "by_category": {k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda x: -x[1])},
        "biggest_expense": {
            "merchant": biggest["merchant"],
            "amount": biggest["amount"],
            "category": biggest["category"],
        },
        "transactions": transactions,
    }


def generate_summary(transactions: list[dict]) -> str:
    if not transactions:
        return (
            "No spending recorded this week — either you were super frugal or forgot to send receipts! "
            "Start sending me your receipts and I'll keep track for you."
        )

    import json
    data_summary = _build_data_summary(transactions)

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": WEEKLY_PROMPT.format(data=json.dumps(data_summary, indent=2)),
            }
        ],
    )
    return message.content[0].text.strip()


def run(monthly: bool = False) -> None:
    if monthly:
        transactions = sheets.get_current_month_transactions()
        period = f"month of {date.today().strftime('%B %Y')}"
    else:
        transactions = sheets.get_current_week_transactions()
        period = f"week ending {date.today().strftime('%b %d, %Y')}"

    print(f"Fetched {len(transactions)} transactions for {period}")

    summary = generate_summary(transactions)
    print(f"\nSummary:\n{summary}\n")

    sid = wa.send_to_owner(summary)
    print(f"Sent via WhatsApp. Message SID: {sid}")


if __name__ == "__main__":
    monthly = "--month" in sys.argv
    run(monthly=monthly)
