import io
import json
import socket
import ssl
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock
from configure_telegram import SetupError, connection_reason, private_chats, save_values, telegram_read

class TelegramSetup(unittest.TestCase):
    def response(self, result):
        return io.StringIO(json.dumps({'ok': True, 'result': result}))

    def test_retry_then_success(self):
        opener = Mock(side_effect=[urllib.error.URLError(TimeoutError()), self.response({'username': 'demo_bot'})])
        sleep = Mock()
        result = telegram_read('SECRET', 'getMe', opener=opener, sleeper=sleep, output=Mock())
        self.assertEqual(result['username'], 'demo_bot')
        self.assertEqual(opener.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_timeout_is_bounded_and_never_prints_token(self):
        token = 'private-secret-token'
        opener = Mock(side_effect=urllib.error.URLError(TimeoutError('https://api.telegram.org/bot' + token)))
        output = Mock()
        with self.assertRaises(SetupError) as error:
            telegram_read(token, 'getUpdates', opener=opener, sleeper=Mock(), output=output)
        self.assertEqual(opener.call_count, 3)
        self.assertIn('timed out', str(error.exception))
        self.assertNotIn(token, str(error.exception))
        self.assertNotIn(token, str(output.call_args_list))

    def test_invalid_token_not_retried(self):
        opener = Mock(side_effect=urllib.error.HTTPError('secret-url', 401, 'Unauthorized', {}, None))
        with self.assertRaises(SetupError):
            telegram_read('SECRET', 'getMe', opener=opener, sleeper=Mock(), output=Mock())
        self.assertEqual(opener.call_count, 1)

    def test_server_error_retried(self):
        opener = Mock(side_effect=[urllib.error.HTTPError('secret-url', 503, 'Unavailable', {}, None), self.response([])])
        self.assertEqual(telegram_read('SECRET', 'getUpdates', opener=opener, sleeper=Mock(), output=Mock()), [])

    def test_certificate_check_never_disabled(self):
        opener = Mock(side_effect=urllib.error.URLError(ssl.SSLCertVerificationError('private-url')))
        with self.assertRaises(SetupError) as error:
            telegram_read('SECRET', 'getMe', opener=opener, sleeper=Mock(), output=Mock())
        self.assertIn('Keep verification enabled', str(error.exception))
        self.assertEqual(opener.call_count, 1)

    def test_dns_error_is_clear(self):
        self.assertEqual(connection_reason(urllib.error.URLError(socket.gaierror())), 'DNS lookup failed')

    def test_private_chat_filter(self):
        updates = [{'message': {'chat': {'id': 1, 'type': 'private'}}}, {'message': {'chat': {'id': -2, 'type': 'group'}}}, {'message': {'chat': {'id': 1, 'type': 'private'}}}]
        self.assertEqual([c[0] for c in private_chats(updates)], ['1'])

    def test_save_preserves_other_keys_and_is_private(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text('RETELL_API_KEY=original\nTELEGRAM_BOT_TOKEN=\nTELEGRAM_CHAT_ID=\n')
            save_values(path, {'TELEGRAM_BOT_TOKEN': 'secret'})
            self.assertIn('RETELL_API_KEY=original', path.read_text())
            self.assertIn('TELEGRAM_BOT_TOKEN=secret', path.read_text())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(len(list(Path(folder).iterdir())), 1)

    def test_save_refuses_multiline(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text('KEEP=yes\n')
            with self.assertRaises(SetupError):
                save_values(path, {'TOKEN': 'bad\nline'})
            self.assertEqual(path.read_text(), 'KEEP=yes\n')

    def test_bad_json_retried(self):
        opener = Mock(side_effect=[io.StringIO('not-json'), self.response([])])
        self.assertEqual(telegram_read('SECRET', 'getUpdates', opener=opener, sleeper=Mock(), output=Mock()), [])

if __name__ == '__main__':
    unittest.main()
