"""
Google Sheets operations for the spending tracker.
Creates and manages the 'Spending Tracker' spreadsheet.
"""

import os
from datetime import datetime, date, timedelta

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_NAME = "Transactions"
HEADERS = ["Date", "Merchant", "Amount", "Currency", "Category", "Notes", "Logged At"]


def _get_service():
    creds = None
    token_path = "token.pickle"
    credentials_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")

    # On cloud servers, load token from env var instead of file
    google_token_b64 = os.environ.get("GOOGLE_TOKEN_B64")
    if google_token_b64 and not os.path.exists(token_path):
        import base64
        with open(token_path, "wb") as f:
            f.write(base64.b64decode(google_token_b64))

    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return build("sheets", "v4", credentials=creds)


def get_or_create_spreadsheet(title: str = "Spending Tracker") -> str:
    """Return spreadsheet ID, creating it with headers if it doesn't exist."""
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")

    service = _get_service()
    sheets = service.spreadsheets()

    if not spreadsheet_id:
        body = {
            "properties": {"title": title},
            "sheets": [{"properties": {"title": SHEET_NAME}}],
        }
        result = sheets.create(body=body).execute()
        spreadsheet_id = result["spreadsheetId"]
        sheet_id = result["sheets"][0]["properties"]["sheetId"]
        print(f"Created spreadsheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        print(f"Add this to your .env: SPREADSHEET_ID={spreadsheet_id}")

        # Write headers
        sheets.values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{SHEET_NAME}!A1",
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()

        # Format header row bold
        sheets.batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "repeatCell": {
                            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                            "fields": "userEnteredFormat.textFormat.bold",
                        }
                    }
                ]
            },
        ).execute()
    else:
        # Ensure headers exist
        result = sheets.values().get(
            spreadsheetId=spreadsheet_id, range=f"{SHEET_NAME}!A1:G1"
        ).execute()
        if not result.get("values"):
            sheets.values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{SHEET_NAME}!A1",
                valueInputOption="RAW",
                body={"values": [HEADERS]},
            ).execute()

    return spreadsheet_id


def append_transaction(transaction: dict) -> None:
    """Append a single spending record to the sheet."""
    spreadsheet_id = get_or_create_spreadsheet()
    service = _get_service()

    row = [
        transaction["date"],
        transaction["merchant"],
        transaction["amount"],
        transaction["currency"],
        transaction["category"],
        transaction.get("notes", ""),
        datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    ]

    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{SHEET_NAME}!A:G",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()


def get_transactions_for_period(start: date, end: date) -> list[dict]:
    """Return all transactions between start and end dates (inclusive)."""
    spreadsheet_id = get_or_create_spreadsheet()
    service = _get_service()

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{SHEET_NAME}!A:G",
    ).execute()

    rows = result.get("values", [])
    if len(rows) <= 1:
        return []

    transactions = []
    for row in rows[1:]:  # skip header
        if not row:
            continue
        # Pad short rows
        row = row + [""] * (7 - len(row))
        try:
            tx_date = datetime.strptime(row[0], "%Y-%m-%d").date()
        except ValueError:
            continue

        if start <= tx_date <= end:
            transactions.append(
                {
                    "date": row[0],
                    "merchant": row[1],
                    "amount": float(row[2]) if row[2] else 0.0,
                    "currency": row[3],
                    "category": row[4],
                    "notes": row[5],
                }
            )

    return transactions


def get_current_week_transactions() -> list[dict]:
    today = date.today()
    start = today - timedelta(days=today.weekday())  # Monday
    return get_transactions_for_period(start, today)


def get_current_month_transactions() -> list[dict]:
    today = date.today()
    start = today.replace(day=1)
    return get_transactions_for_period(start, today)
