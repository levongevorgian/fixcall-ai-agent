#!/usr/bin/env python3
import json,os,urllib.request
from server import load_env
load_env()
token=os.getenv('TELEGRAM_BOT_TOKEN','')
if not token:raise SystemExit('Set TELEGRAM_BOT_TOKEN in .env first, then press Start in your bot chat.')
try:
 request=urllib.request.Request('https://api.telegram.org/bot'+token+'/getUpdates',headers={'Accept':'application/json'})
 with urllib.request.urlopen(request,timeout=10) as r:data=json.load(r)
except Exception:raise SystemExit('Could not retrieve bot updates. Check your token and network; the token is not printed.') from None
seen=set()
for update in data.get('result',[]):
 chat=(update.get('message') or {}).get('chat',{})
 if chat.get('id') is not None and chat['id'] not in seen:
  print(json.dumps({'chat_id':chat['id'],'name':chat.get('title') or chat.get('first_name'),'type':chat.get('type')}));seen.add(chat['id'])
if not seen:print('No chats found. Open your bot in Telegram, press Start, and rerun this helper.')
