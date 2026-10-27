#!/usr/bin/env python3
"""Ask for credentials locally without putting secrets in chat or command history."""
import getpass
import os
import secrets
from pathlib import Path
ROOT=Path(__file__).resolve().parent
path=ROOT/'.env'
if path.exists():
    raise SystemExit('.env already exists. Edit it locally to preserve your current settings.')
print('Credentials stay in your local .env and are excluded from submission archives.')
values={
    'RETELL_API_KEY':getpass.getpass('Retell API key (leave blank to configure later): ').strip(),
    'RETELL_AGENT_ID':'',
    'PUBLIC_BASE_URL':input('Public HTTPS backend URL (blank for now is okay): ').strip(),
    'DASHBOARD_TOKEN':secrets.token_urlsafe(32),
    'TOOL_TOKEN':secrets.token_urlsafe(32),
    'TELEGRAM_BOT_TOKEN':getpass.getpass('Telegram bot token (blank for now is okay): ').strip(),
    'TELEGRAM_CHAT_ID':input('Telegram destination chat ID (blank for now is okay): ').strip(),
    'RETELL_VOICE_ID':'',
    'HOST':'127.0.0.1','PORT':'8765'}
if any('\n' in v or '\r' in v for v in values.values()):raise SystemExit('Values must be single-line.')
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f:f.write('\n'.join(k+'='+v for k,v in values.items())+'\n')
print('Saved .env. Use its DASHBOARD_TOKEN to open your local feed. Restart the server after changes.')
