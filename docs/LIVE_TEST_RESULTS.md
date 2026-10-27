# Live validation — October 27, 2026

Levon spoke the calls through Retell Test Audio and the public Voice Orb using fictional customer details. Transcripts, tool results and persistent records were inspected. No real appointments were scheduled.

| Scenario | Verified behavior | Evidence |
|---|---|---|
| Standard request | Phone confirmed; $99 disclosed and accepted; request saved | REQ-34C3C88F |
| LG warranty | Unclear brand clarified; $0 service fee; request saved | REQ-9899C95F |
| Warranty representative | Company, name, phone and job saved; callback promise; no booking or fee | MSG-951C8A31, MSG-22C7693A |
| Spam | Brief refusal and hangup; no booking/message | call_ea094233b4bfddbf5fdbcdd3e81 |
| Fee refusal | No booking; message offered | call_a06e006f52e625c3a8a6c43dfa7 |
| Warranty after paid quote | Route changed and fee removed before handoff | REQ-8956CFE6 |
| Representative confirmation | Company and phone readback confirmed; Cimo voice approved by Levon | call_51b274b61420eb7deee3da59a53 |
| Shared-link standard call | Fee consent and handoff succeeded | REQ-ADC20F3C |
| Shared-link LG regression | Misheard LG clarified; $99 accepted; correct brand and request saved | REQ-9517292C, call_869bb7391415045f6f4414be2b5 |
| Reviewer notification interface | Latest successful call and analyzed summary retrieved through protected public reviewer API; browser page loads | call_869bb7391415045f6f4414be2b5 |
| Telegram delivery | Real standard, warranty, representative and spam notifications received; fee-refusal arrived after delay | User confirmed contents; durable outbox records acknowledgements |

## Failures found and changes

The first standard test stored a malformed 12-digit US callback number. Backend validation now rejects it and phone readback is required; later standard calls stored confirmed valid numbers.

A shared call transcribed spoken LG as “an allergy”; the model wrongly rejected it. Context-preserving clarification and boosted brand keywords were published in version 1. The next shared call correctly asked “Did you say L G?”, continued and saved LG. That retest still repeated brand confirmation and goodbye.

Final published version 2 retains all business rules and adds confirmed-field memory and immediate end_call after one closing. The Voice Orb Share dialog was explicitly switched to version 2 and verified. These last conversation-polish changes have configuration readback and 61 passing automated tests; a final spoken retest remains pending. Automated tests are not proof of natural conversation behavior.

Customer company labels are suppressed; extraction now distinguishes appliance brands from represented companies. Company/phone readback and corrected symptom wording were added.

## Free reviewer setup

A dedicated read-only key allows GET-only access to non-synthetic calls after the review window began. Anonymous call-data access returns 401; authorized public read returns 200. The administrative key remains local. Reviewer write requests are rejected and historical calls are excluded, verified by tests. Credentials are excluded from the source archive and repository.

No paid Render service was created. The optional paid blueprint was moved out of the root directory. Review requires a powered, awake laptop, internet, local backend and free Cloudflare tunnel during an agreed window. A tunnel failed earlier and was replaced; there is no unattended uptime guarantee. If its address changes, tools/webhook and the published shared version must be updated before review.

Telegram transport intermittently times out on this network. Its queue retries and preserves pending messages, but the protected browser feed is the primary review interface. Telegram is supplementary, and delivery timing is not guaranteed. An exceptional crash between sending and storing an acknowledgement may cause a duplicate Telegram message.

## Coverage limits

61 automated tests passed. Samsung and GE aliases, hangups, concurrency, authentication and additional edge cases have automated coverage; not every proposed live test was spoken. Cimo naturalness was approved by Levon; no formal three-voice comparison was performed. No finite tests establish that a model can never hallucinate.
