# Reviewer guide

This submission includes the conversation prompt, Retell API configuration templates, a working Python backend, a protected notification feed, Telegram integration, tests, and live validation notes.

## Review in five minutes

1. Read README.md and docs/LIVE_TEST_RESULTS.md for the verified scope and limitations.
2. Inspect agent/prompt.md for the four caller routes and exception behavior.
3. Run `python3 -m unittest discover -s tests -v` from the project folder.
4. For an offline feed demonstration, run `python3 demo.py`, then `python3 server.py`; open http://127.0.0.1:8765 and enter the local access key. Synthetic records never send Telegram messages.
5. For live Retell and Telegram setup, follow docs/SETUP.md using your own credentials. Templates are sanitized API payloads, not dashboard import files.

## Expected demonstrations

- Standard request: collect details, read back phone, disclose $99, wait for explicit agreement, then hand off.
- LG/Samsung/GE warranty volunteered by customer: $0 service-call fee, including when mentioned after a paid quote.
- Warranty-company representative: message with company, name, callback and job; no repair booking.
- Spam: brief refusal and hangup.
- Refused fee: no booking.

The booking function persists a repair request and returns a reference. No calendar/provider was supplied, so it does not reserve an appointment. n8n was replaced by a durable Python notification worker.

Live reviewer access must be arranged separately. No credentials, customer database, private dashboard key or public voice-orb token are included in this archive.
