# Workflow: Weekly Spending Summary

## Objective
Every Sunday evening, automatically pull this week's transactions from Google Sheets, generate a friendly spending summary with Claude, and send it to the user via WhatsApp.

## Tool Used
`tools/weekly_summary.py`

## Schedule Options

### Option A: Mac cron job (runs while your Mac is on)
Open Terminal and run:
```bash
crontab -e
```
Add this line (runs every Sunday at 8 PM):
```
0 20 * * 0 cd /Users/brianvu/Automation\ && source .venv/bin/activate && python tools/weekly_summary.py >> .tmp/summary.log 2>&1
```

### Option B: Run manually anytime
```bash
cd /Users/brianvu/Automation\ 
python tools/weekly_summary.py          # weekly summary
python tools/weekly_summary.py --month  # monthly summary
```

### Option C: Scheduled via Claude Code (cron)
Ask Claude to set up a schedule using the `schedule` skill.

## What the Summary Includes
- Total spending for the week
- Breakdown by category (sorted by amount)
- Biggest single expense
- One personalized savings tip from Claude
- Motivational closing line

## Inputs
- Google Sheets: current week's transaction rows (auto-fetched)
- ANTHROPIC_API_KEY: for Claude summary generation
- TWILIO credentials + OWNER_WHATSAPP_NUMBER: for delivery

## Outputs
- WhatsApp message sent to OWNER_WHATSAPP_NUMBER
- Log printed to stdout / .tmp/summary.log

## Edge Cases
- **No transactions this week**: Sends a friendly reminder to log receipts
- **Google Sheets auth expired**: Re-run `python tools/setup_sheets.py` to refresh
- **Twilio error**: Check TWILIO credentials in .env; script prints error to stdout

## Sample Output Message
```
Here's your week, Brian! 🧾

You spent $234.50 across 12 transactions this week.

Food & Dining: $89.00
Transport: $45.00
Groceries: $38.50
Shopping: $32.00
Entertainment: $30.00

Biggest hit: Dinner at Nobu ($45.00).

Tip: Dining out is your #1 expense this week — cooking just 2 more meals at home could save you $30+.

You're doing great — small steps add up! 💪
```
