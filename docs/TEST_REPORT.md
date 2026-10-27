# Automated test report

59 tests passed on October 27, 2026 using Python 3.13 on the local development machine (49 core/integration tests and 10 Telegram-setup tests).

Command: `python3 -m unittest discover -s tests -v`

Coverage includes paid-service consent and evidence, warranty aliases, unsupported warranty fallback, stale quotes, duplicate/concurrent booking attempts, representative messages, caller hangup records, duplicate/out-of-order webhooks, durable notification retry, Telegram send/edit behavior with mocked transport, signature verification, authenticated dashboard access, and signed HTTP tool/webhook requests.

No paid Retell calls or Telegram messages were sent by these tests. Telegram network transport was mocked. Synthetic browser examples are demonstration data, not completed live calls. See LIVE_TEST_RESULTS.md for actual live results and remaining external checks.

Telegram setup helper: 10 additional isolated tests passed for retries, timeout bounds, token-safe errors, certificate verification, private-chat filtering, and atomic private credential storage. No real token or network requests were used by these helper tests.
