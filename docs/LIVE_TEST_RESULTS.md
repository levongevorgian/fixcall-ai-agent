# Live validation — October 27, 2026

Tests were spoken by Levon through Retell Test Audio using fictional customer details. Transcripts, tool outcomes and persistent records were inspected. No real appointments were scheduled.

| Scenario | Observed result | Evidence |
|---|---|---|
| Standard customer | Phone read back and confirmed, $99 explicitly accepted, handoff stored | REQ-34C3C88F |
| LG warranty | Ambiguous brand clarified; fee $0; handoff stored | REQ-9899C95F |
| Warranty representative | Name, company, callback and job stored; no booking or fee | MSG-951C8A31 |
| Spam | Brief refusal and agent hangup; no booking/message | call_ea094233b4bfddbf5fdbcdd3e81 |
| Fee refused | Agent declined to submit and offered a message; no booking | call_a06e006f52e625c3a8a6c43dfa7 |
| Warranty mentioned after $99 quote | New warranty route, $0 fee, successful handoff | REQ-8956CFE6 |
| Representative retest | Introduction company remembered; message stored without booking | MSG-22C7693A |
| Telegram | Actual notifications received by Levon for standard, warranty and spam calls | User confirmed message contents |

## Fixes from testing

The first standard call incorrectly stored a 12-digit US phone number. Validation now rejects malformed US numbers and the prompt requires readback and confirmation. The subsequent standard test passed. The original test remains historical evidence, not a clean pass.

Company names were incorrectly extracted from appliance brands for customer calls. Customer notifications now omit company, and extraction instructions restrict it to a represented business. Symptom instructions now require clear, context-consistent wording. Representative company and phone confirmation was added after a transcription captured “Home Shielded”. Levon subsequently confirmed a refreshed representative test read back the company and callback correctly.

## Operational limitations

Telegram works but the local network intermittently times out. The durable outbox retries; final delivery can be delayed. Transport timeout increased to 25 seconds on the background worker, without blocking call tools. Delivery is at least once across an exceptional crash between sending and saving Telegram acknowledgement.

The temporary Cloudflare address became unreachable during testing and was replaced. Retell was reconnected and subsequent fee-refusal, late-warranty and representative calls reached the backend. The tunnel requires this computer and backend to stay awake and online. A stable host is required for unattended review.

The selected voice is Cimo. Levon confirmed that Cimo sounds clear and natural during the final representative test. A formal three-voice comparison was not performed. Caller hangup and other edge cases have automated coverage but not all thirty proposed live scenarios have been run.

## Reviewer access

The tested agent was published as version 0; Retell then created draft version 1. Retell's Share dialog was inspected again: the voice-orb toggle and copy-link control are currently disabled. No usable public reviewer link has been created or verified. Arrange a supervised dashboard demonstration or finish account sharing and stable hosting before claiming an unattended live submission is ready.

## Shared link and free reviewer setup

Levon enabled Voice Orb sharing and confirmed a successful shared-link call. He confirmed Cimo voice quality and company/phone readback in a final representative call. The paid-hosting route was abandoned at his request; no paid service was created by this agent. A separate restricted dashboard review key now provides GET-only access to calls after the review window began. 61 tests pass. The completed shared-link call call_6d58e60083256926ede2031a06f appeared in the external restricted reviewer feed with its analyzed summary, verifying post-call interface delivery. That same call exposed the LG recognition failure recorded below.

## Brand-transcription failure discovered during final review

Call call_6d58e60083256926ede2031a06f transcribed spoken LG as “an allergy”. The model incorrectly used the spam refusal despite the preceding washer-repair context. This is a failed live regression, not a pass. Prompt updated to preserve repair context, confirm ambiguous brand spellings, and require clear unrelated intent before spam rejection. Retell brand keywords added. The final shared-link retest must establish that LG clarification now continues intake.

The corrected prompt and brand keywords were read back from published version 1. The shared link remains on version 1. Live LG regression retest pending.
