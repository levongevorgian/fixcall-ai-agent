#!/usr/bin/env python3
"""Connect a private Telegram bot chat with safe credential storage and retries."""
import getpass
import json
import os
import socket
import ssl
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from server import ROOT, load_env


class SetupError(Exception):
    pass


def save_values(path, updates):
    """Atomically update selected .env entries without losing other credentials."""
    path = Path(path)
    if not path.exists():
        raise SetupError('Run setup_local.py first.')
    for key, value in updates.items():
        if '\n' in value or '\r' in value:
            raise SetupError('Credential values must be single-line.')
    seen = set()
    lines = []
    for line in path.read_text().splitlines():
        key = line.split('=', 1)[0]
        if key in updates:
            if key not in seen:
                lines.append(key + '=' + updates[key])
                seen.add(key)
        else:
            lines.append(line)
    lines.extend(key + '=' + value for key, value in updates.items() if key not in seen)
    descriptor, temporary = tempfile.mkstemp(prefix='.telegram-setup-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            stream.write('\n'.join(lines) + '\n')
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def connection_reason(error):
    reason = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(reason, ssl.SSLCertVerificationError):
        return 'certificate verification failed'
    if isinstance(reason, socket.gaierror):
        return 'DNS lookup failed'
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return 'connection timed out'
    return 'network connection failed'


def telegram_read(token, method, opener=urllib.request.urlopen, sleeper=time.sleep, output=print):
    """Read bot data only; never log exception strings containing the token URL."""
    for attempt in range(3):
        request = urllib.request.Request(
            'https://api.telegram.org/bot' + token + '/' + method,
            headers={'Accept': 'application/json'},
        )
        try:
            with opener(request, timeout=8) as response:
                data = json.load(response)
            if not isinstance(data, dict) or not data.get('ok'):
                raise SetupError('Telegram did not accept this request. The token remains saved privately.')
            return data.get('result')
        except urllib.error.HTTPError as error:
            if error.code in {401, 404}:
                raise SetupError('Telegram rejected the bot token. Copy the full token from BotFather and rerun to replace it.') from None
            if error.code not in {429, 500, 502, 503, 504}:
                raise SetupError('Telegram returned HTTP ' + str(error.code) + '. No token displayed.') from None
            description = 'Telegram temporarily unavailable (HTTP ' + str(error.code) + ')'
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            description = connection_reason(error)
            if description == 'certificate verification failed':
                raise SetupError('Certificate verification failed in this Python environment. Keep verification enabled and tell Codex this exact message.') from None
        except (json.JSONDecodeError, UnicodeError):
            description = 'unexpected response from Telegram'
        if attempt < 2:
            output(description.capitalize() + '. Retrying (' + str(attempt + 2) + '/3)...')
            sleeper(attempt + 1)
        else:
            raise SetupError(description.capitalize() + ' after three attempts. Your token is saved; rerun later and press Enter to reuse it.') from None


def private_chats(updates):
    chats = {}
    for update in updates or []:
        if not isinstance(update, dict):
            continue
        message = update.get('message') or {}
        chat = message.get('chat') or {}
        if chat.get('type') == 'private' and chat.get('id') is not None:
            chats[str(chat['id'])] = chat
    return list(chats.items())


def main():
    load_env()
    saved = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    prompt = 'Press Enter to reuse the saved bot token, or paste a replacement (hidden): ' if saved else 'Paste your Telegram bot token (hidden): '
    token = getpass.getpass(prompt).strip() or saved
    if not token or any(character.isspace() for character in token):
        raise SetupError('The token must be one nonempty value with no spaces.')
    changes = {'TELEGRAM_BOT_TOKEN': token}
    if token != saved:
        changes['TELEGRAM_CHAT_ID'] = ''
    save_values(ROOT / '.env', changes)
    print('Bot token saved privately. A failed connection will not erase it.')
    bot = telegram_read(token, 'getMe')
    username = bot.get('username', '')
    print('Verified bot: @' + username)
    print('Open https://t.me/' + username + ' in Telegram, press Start, and send Hello.')
    input('Press Enter once you have sent Hello to THIS bot: ')
    options = private_chats(telegram_read(token, 'getUpdates'))
    if not options:
        raise SetupError('No private chat found for @' + username + '. Open that exact bot, send /start and Hello, then rerun and press Enter to reuse the saved token.')
    for index, (chat_id, chat) in enumerate(options, 1):
        name = chat.get('first_name') or chat.get('username') or 'Private chat'
        print(str(index) + '. ' + str(name) + ' (chat ID ' + chat_id + ')')
    choice = input('Choose YOUR private chat by number: ').strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(options):
        raise SetupError('No valid chat selected. The bot token remains saved; no new chat destination was selected.')
    save_values(ROOT / '.env', {'TELEGRAM_CHAT_ID': options[int(choice) - 1][0]})
    print('Telegram connection saved privately. No messages sent by this helper. Tell Codex it is saved.')


if __name__ == '__main__':
    try:
        main()
    except SetupError as error:
        raise SystemExit(str(error)) from None
    except (KeyboardInterrupt, EOFError):
        raise SystemExit('\nSetup stopped. Any previously saved token remains private.') from None
