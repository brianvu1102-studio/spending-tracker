"""
One-time setup: create the Google Sheets spreadsheet and print its ID.
Run this once, then add SPREADSHEET_ID to your .env.

Usage:
    python tools/setup_sheets.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import tools.sheets_manager as sheets

if __name__ == "__main__":
    print("Setting up Google Sheets...")
    spreadsheet_id = sheets.get_or_create_spreadsheet()
    print(f"\nDone. Spreadsheet ID: {spreadsheet_id}")
    print(f"View it at: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

    if not os.environ.get("SPREADSHEET_ID"):
        print(f"\nAdd this line to your .env file:")
        print(f"SPREADSHEET_ID={spreadsheet_id}")
