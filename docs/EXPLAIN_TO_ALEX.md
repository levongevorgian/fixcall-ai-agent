# Explain the solution

## Short walkthrough

I built a voice receptionist that recognizes the caller's purpose from the conversation. It uses a common intake for repair customers, changes route if a supported warranty is mentioned, takes messages from warranty company representatives, and ends unrelated calls briefly.

The prompt handles natural conversation, while the backend checks important actions. For standard jobs, the backend requires a valid quote and evidence that the customer accepted the $99 fee. It blocks old quotes after a warranty change and prevents repeated requests from creating duplicate handoffs.

After a call ends, a persistent notification record appears in the dashboard. Telegram delivery runs separately with retries, and the message can be updated when the final analysis arrives. A delivery failure does not erase the call record.

No booking calendar was supplied, so I implemented the booking function as a persistent handoff with a reference. The agent explicitly avoids claiming a confirmed appointment time. I documented unsupported warranty handling rather than inventing a business policy.

## Likely follow-up questions

**Why use a backend instead of putting every rule in the prompt?**
A prompt guides the conversation, but important actions should also be checked in code. The backend can reject an invalid fee agreement or stale quote even if the model calls the tool incorrectly.

**Why one prompt?**
The required routes are small enough to keep the instructions together, and the caller may change the route midway. The tools still enforce separate outcomes. If the workflow grows, explicit conversation states would make it easier to maintain.

**Why not n8n?**
It was recommended rather than required. Direct delivery let me keep storage, retries, and notification updates in one small implementation. The webhook boundary can connect to n8n later.

**How did you choose the voice?**
Only answer after testing. State the voices compared, selected ID, the same test sentences used, and the actual pace/interruption findings. Do not claim an audition happened before it did.

**What remains a limitation?**
Caller intent and extracted fields still depend on the model. The backend checks the action arguments and evidence, but full conversation correctness needs live evaluation. There is also no real appointment calendar in the supplied brief.

**How did you use AI while building?**
Be transparent about the help received. Explain which decisions you reviewed, how you checked the implementation, and demonstrate that you understand the code. Do not claim every line was written without assistance.

## Read these functions before the follow-up

- core.py: prepare, book, message, webhook, consent_evidence
- server.py: signature checks and notification_worker
- configure.py: custom tool definitions and Retell setup
- agent/prompt.md: contextual routes and speech rules

Be able to explain a standard call, a warranty disclosed late, and a webhook arriving twice without reading a script.
