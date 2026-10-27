# Implementation decisions

## Architecture

Retell hosts the speech recognition, LLM conversation, and selected female voice. Three signed custom functions call a small Python backend. SQLite stores quotes, booking handoffs, callback messages, call summaries, and an outbox. A browser feed displays call records. A background worker sends Telegram notifications and edits the same message after analysis arrives.

The backend deliberately uses Python's standard library so the demo has no installation dependencies. For a high-traffic production deployment replace the demo HTTP server with a production gateway/application server, introduce managed storage, and monitor delivery backlog. This is a single-instance assessment implementation.

## Requirements traceability

| Requirement | Implementation |
|---|---|
| Natural identification of caller | Open greeting, contextual routing in prompt, no universal checklist |
| Standard customer intake | Six required fields validated in prepare_booking |
| $99 disclosed and accepted before booking | Latest quote required; exact affirmative words checked against signed call transcript after a $99 agent disclosure |
| Supported warranty brands | Backend normalizes LG, Samsung, GE and General Electric aliases |
| Warranty mentioned late | New quote invalidates prior quotes; details retained |
| Warranty representative | Separate take_message tool; representative blocked from quote preparation |
| Spam | Brief refusal and end_call; post-call webhook still recorded |
| No unsupported facts | Prompt limits, no calendar claims, returned tool outcomes are authoritative |
| Female natural voice | Configurable live-selected female voice; audition checklist and starting settings |
| Notification interface | Protected local web feed plus Telegram send/edit worker |
| Reliable delivery | SQLite outbox, retry/backoff, event deduplication, event-order protection |

## Explicit assumptions

1. No scheduling calendar, business hours, service-area list, or real booking endpoint was supplied. The booking function therefore implements a real persistent handoff, not a calendar appointment. The response explicitly says appointment_confirmed=false. If the reviewer requires selecting a live slot, they must provide the target booking system or permit a clearly identified demo calendar; do not invent business availability.
2. Unsupported warranty brands are message-only. The task gives no rule authorizing conversion to paid service, denial of all service, or reimbursement promises.
3. General Electric and GE mean the same brand. No warranty is inferred from a brand alone.
4. Other relevant calls go to messages; the only business phone line can receive existing-job requests.
5. The greeting uses generic appliance repair because no trading name was supplied.
6. The task's instruction to send summaries is implemented to the configured owner's Telegram chat. No customer SMS is sent.
7. Browser calls are the initial live test method; an inbound phone number is optional and requires additional account/telephony setup.

## Trust boundaries and limits

Retell signature verification uses raw request bytes, HMAC SHA-256, and a five-minute timestamp window, matching the official SDK implementation. Custom tools also require a separate secret token. Dashboard data requires a bearer access key; the key is not embedded in URLs. Client rendering uses textContent rather than HTML insertion. Credentials, database contents, and local demo access keys are excluded from archives.

The backend checks structure and fee evidence, but the model still interprets caller intent and extracts fields. A valid signature proves request origin, not the truth of every model-generated argument. Consent checks are intentionally conservative and may ask for a clearer answer. Call recordings/transcripts and live adversarial tests are required before claiming robust conversational compliance.

A prepared quote records the number of transcript turns observed at preparation. Consent must occur after that point. This assumes Retell's custom-function call object includes an append-only transcript in transcript_object or standard Agent:/User: form. If transcript evidence is absent, standard booking fails closed. Verify this with an actual Retell call before submission.

Notifications are queued within the same transaction as the call record and network delivery happens afterward. call_ended creates an initial notification; call_analyzed updates the same message using its stored Telegram message ID. Delivery is at-least-once: a process crash after Telegram accepts a send but before its message ID is saved can produce a duplicate. Single-worker operation avoids normal concurrent sends, but exactly-once delivery across that crash boundary is not claimed.

Tool-confirmed identity, booking reference, fee, and outcome take precedence over model post-call extraction. Summary text itself remains model-generated; it is displayed separately from the authoritative fields. Synthetic examples are marked and excluded from Telegram delivery.

## Official integration references

- https://docs.retellai.com/api-references/create-retell-llm
- https://docs.retellai.com/api-references/create-agent
- https://docs.retellai.com/api-references/list-voices
- https://docs.retellai.com/features/webhook-overview
- https://docs.retellai.com/features/secure-webhook
- https://github.com/RetellAI/retell-python-sdk/blob/main/src/retell/lib/webhook_auth.py
- https://core.telegram.org/bots/api#sendmessage
- https://core.telegram.org/bots/api#editmessagetext
