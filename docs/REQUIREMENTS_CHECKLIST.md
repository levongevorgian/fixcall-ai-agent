# Assessment requirements and evidence

Source: Alex's supplied AI_Agent_Test_Task.md.pdf. Recommended tools are recommendations, not mandatory platform subscriptions.

| Requirement | Implementation and evidence | Limit |
|---|---|---|
| Recognize caller from conversation | Prompt uses context; all four main routes live-tested | Not every possible conversation tested |
| Standard intake: appliance, issue, brand, name, phone, address | Persistent validated tool fields; phone readback live-tested | Missing fields cause clarification/message fallback |
| $99 heard and accepted before booking handoff | Server validates explicit agreement against transcript; paid and refusal scenarios live-tested | No appointment calendar supplied |
| Warranty only when caller raises it; LG/Samsung/GE fee-free | Brand aliases and late route changes tested automatically; LG and late disclosure live-tested | Samsung/GE not independently voice-tested |
| Representative message, no booking | Name, company, phone, job stored; callback promise; live-tested | No invented callback deadline |
| Spam: short refusal then end | Live transcript and agent hangup verified | Ambiguous greetings are clarified |
| No invented prices, timelines or capabilities | Prompt limits; backend fee gate and truthful tool outcomes | Cannot guarantee zero model errors in every input |
| Natural English, female voice, one question at a time | Cimo selected; Levon confirmed clear natural voice; prompt/turn-taking refined | Subjective quality assessed by Levon, not comparative acoustic study |
| Notification after call in actual interface | Signed call-ended/analyzed webhooks, persistent browser feed; Telegram messages received | Telegram intermittent; browser feed is primary review interface |
| Live testable complete implementation | Shared Voice Orb call completed by Levon; source and 61 automated tests provided | Free tunnel requires laptop online; restricted-feed delivery verified; LG clarification regression passed; final conversation-polish retest pending |

Booking is a persistent handoff with a reference, matching the supplied task's booking-function handoff. Unsupported warranty brands use a documented message fallback because the task gives no conversion policy. No payment collection, technician timetable or full repair price is invented.
