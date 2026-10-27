# Appliance repair voice agent

A FixCall AI assessment implementation with a Retell conversation prompt, validated booking handoff, callback messages, a protected call-notification feed, and Telegram delivery.

**Current status:** 59 automated tests passed. Live standard, LG warranty, representative, spam, fee-refusal and late-warranty scenarios were verified. Telegram delivery was confirmed, with intermittent network delays. External reviewer access and stable hosting remain to be completed. See docs/LIVE_TEST_RESULTS.md.

## Start locally

Requires Python 3.11 or newer. No third-party Python packages are needed.

```sh
python3 server.py
```

Open http://127.0.0.1:8765/. Enter the key from `runtime/dashboard-key.txt` when starting without an environment file. For live setup, run `python3 setup_local.py` and use DASHBOARD_TOKEN from your private `.env` instead.

Optional synthetic examples:

```sh
python3 demo.py
```

These only populate the local feed. They are marked synthetic and never sent to Telegram.

Run checks:

```sh
python3 -m unittest discover -s tests -v
```

## What is implemented

- Contextual handling of ordinary customers, supported-brand warranty customers, warranty company representatives, and spam.
- Six-field customer intake and a $99 fee agreement gate for standard requests.
- Fee-free warranty routing for LG, Samsung, and General Electric/GE when the customer mentions warranty.
- A persistent booking handoff with a reference, not an invented appointment time.
- Separate callback messages for representatives and other relevant requests.
- Signed Retell tool/webhook endpoints, local call feed, and Telegram notification outbox with retries.
- Event deduplication and updating an existing Telegram notification when analysis arrives.

## Read next

- [Live setup](docs/SETUP.md)
- [Agent prompt](agent/prompt.md)
- [Design and assumptions](docs/DESIGN.md)
- [Thirty live conversation tests](docs/ACCEPTANCE_TESTS.md)
- [Actual validation status](docs/LIVE_TEST_RESULTS.md)
- [Explain the solution to Alex](docs/EXPLAIN_TO_ALEX.md)

## Important scope

The assignment supplies no calendar or booking provider. `book_repair` therefore stores and acknowledges a booking handoff. It never claims an appointment has been scheduled. Unsupported warranty brands go to a message because no paid-conversion policy was supplied.

Retell, n8n, and Telegram are recommendations in the assignment. This implementation uses Retell and direct Python-to-Telegram delivery; n8n is not required. SQLite makes the notification queue inspectable and durable without an additional hosted automation dependency.

Do not submit `.env`, runtime files, caller data, or API credentials. Use `python3 package_submission.py` to create a clean archive after live testing and updating the validation record.
