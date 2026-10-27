# Reviewer guide

## Live review

Levon supplies the Voice Orb link, notification dashboard address and a separate read-only key privately. Open both links, enter the key in the dashboard and complete a fictional call in the voice-agent page. End the call, then watch the feed update. It displays call type, collected details, outcome, reference and analyzed summary. Final analysis may follow the first call-ended record.

Review during an agreed window: the free backend runs on Levon's laptop through an HTTPS tunnel. It must remain online. Telegram is an additional channel with observed connectivity delays; the dashboard is the primary post-call interface.

## Suggested checks

- Standard repair: describe appliance/issue/brand and give name, callback and service address. A $99 fee must be heard and accepted before handoff.
- LG/Samsung/GE warranty: volunteer warranty, including after the fee quote. Eligible jobs have no service-call fee.
- Home warranty company representative: provide company, name, callback and job. Expect a message and callback promise, not a booking.
- Spam: unrelated sales should receive a brief refusal and hangup.
- Declined fee: no booking should be submitted.

No calendar was supplied. Booking means a persisted repair-request handoff with a reference, not a reserved appointment. Unsupported warranty brands use a documented message fallback. No repair-price total, technician timetable or coverage verification is invented.

## Source review

Read agent/prompt.md, docs/REQUIREMENTS_CHECKLIST.md and docs/LIVE_TEST_RESULTS.md. Run `python3 -m unittest discover -s tests -v` from the project folder. The source includes setup helpers and sanitized API templates; templates are not Retell dashboard-import bundles. Credentials and caller databases are excluded.

For a purely local synthetic demonstration, run `python3 demo.py`, then `python3 server.py`; open http://127.0.0.1:8765 and use the local access key. Synthetic examples never send Telegram messages. Live setup is documented in docs/SETUP.md and docs/FREE_REVIEW.md.
