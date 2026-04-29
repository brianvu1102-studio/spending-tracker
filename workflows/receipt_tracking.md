# Workflow: Receipt Tracking via WhatsApp

## Objective
Receive WhatsApp receipts (photo or text) from the user, extract spending data with Claude, and save to Google Sheets.

## How It Works
1. User sends a receipt photo or text to the Twilio WhatsApp number
2. Twilio forwards it to the webhook server (`tools/webhook_server.py`)
3. Claude extracts: merchant, date, amount, currency, category, notes
4. Data is appended to the "Spending Tracker" Google Sheet
5. The bot replies with a confirmation message

## Inputs
- Receipt image (JPEG/PNG) OR text description (e.g. "Grab $8.50 transport")
- Twilio webhook POST from Twilio servers

## Tools Used
| Tool | Purpose |
|------|---------|
| `tools/webhook_server.py` | Flask server, Twilio webhook endpoint |
| `tools/process_receipt.py` | Claude API receipt extraction |
| `tools/sheets_manager.py` | Append/read Google Sheets rows |

## Setup (One-Time)

### Step 1: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Create your .env file
Copy `.env.example` to `.env` and fill in:
```
ANTHROPIC_API_KEY=sk-ant-...
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=+14155238886    # Twilio sandbox number
OWNER_WHATSAPP_NUMBER=+your_number   # Your WhatsApp number (E.164 format)
GOOGLE_CREDENTIALS_PATH=credentials.json
SPREADSHEET_ID=                      # Leave blank for now
```

### Step 3: Google Sheets auth
Download `credentials.json` from Google Cloud Console (OAuth 2.0 Desktop app):
- Go to console.cloud.google.com → APIs & Services → Credentials
- Create OAuth 2.0 Client ID (Desktop app) → Download JSON → save as `credentials.json`
- Enable the Google Sheets API for your project

### Step 4: Create the spreadsheet
```bash
python tools/setup_sheets.py
```
Copy the printed `SPREADSHEET_ID` into your `.env`.

### Step 5: Set up Twilio WhatsApp Sandbox
- Go to twilio.com → Messaging → Try it Out → Send a WhatsApp message
- Follow the sandbox join instructions (send a code from your WhatsApp)
- Note your sandbox number (e.g. +14155238886)

### Step 6: Start the webhook server
```bash
python tools/webhook_server.py
```

### Step 7: Expose with ngrok (for local development)
```bash
ngrok http 5001
```
Copy the HTTPS URL (e.g. `https://abc123.ngrok.io`) and set as Twilio sandbox webhook:
- Twilio Console → Sandbox → "When a message comes in" → paste `https://abc123.ngrok.io/webhook`

## User Commands (WhatsApp)
| Message | Action |
|---------|--------|
| Photo of receipt | Extract and log automatically |
| `Starbucks $5.50` | Log from text description |
| `summary` | Show this week's spending total by category |
| `help` | Show usage instructions |

## Categories
Claude auto-assigns one of: Food & Dining, Groceries, Transport, Entertainment, Shopping, Health & Medical, Utilities, Other

## Edge Cases
- **Blurry image**: Bot replies asking for a clearer photo or text description
- **Missing date on receipt**: Defaults to today's date
- **Non-image media**: Bot rejects with a helpful message
- **Google Sheets auth expired**: Re-run `setup_sheets.py` to refresh OAuth token

## Deployment (Always-On)
For 24/7 availability without ngrok, deploy to Render.com (free tier):
1. Push code to GitHub
2. Create a new Web Service on Render, pointing to this repo
3. Set Start Command: `python tools/webhook_server.py`
4. Add all .env variables in Render's Environment settings
5. Use the Render HTTPS URL as your Twilio webhook
