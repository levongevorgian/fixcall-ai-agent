# Live setup

The code and local tests are prepared. Complete these steps before presenting the agent as ready for Alex to test.

## 1 Create your Retell account

Open https://dashboard.retellai.com/ and create an account. Complete account verification yourself. Check available credits and pricing before placing calls. A phone number is not required for the initial browser-call tests.

Get an API key from your workspace's API key settings. Use the key designated for webhook verification when the account exposes that distinction. Keep it private.

## 2 Save local credentials

From the project folder run:

```sh
python3 setup_local.py
```

Enter credentials in the terminal prompts. They are saved in `.env` with private file permissions. You may leave values blank until ready. Never paste tokens into a public repository, submission message, or screenshot.

Start the backend:

```sh
python3 server.py
```

Open http://127.0.0.1:8765/ and enter DASHBOARD_TOKEN from `.env`. If you started without `.env`, the server instead writes a temporary local key to `runtime/dashboard-key.txt`.

## 3 Connect Telegram

In Telegram, open the verified @BotFather account. Create a bot using /newbot and choose its name and username. Save the returned bot token in TELEGRAM_BOT_TOKEN in your local `.env`.

Open a private chat with your new bot and press Start. To find the chat ID without exposing the token in a browser URL, use the helper:

```sh
python3 telegram_setup.py
```

It reads the token from `.env` and displays chat IDs/names from received updates. Choose your own private chat and save its ID as TELEGRAM_CHAT_ID. Restart the backend. The first real completed call will send a notification; synthetic demo fixtures are never sent.

This implementation sends plain text to avoid HTML/Markdown injection from caller speech. After analysis arrives, it edits the initial message instead of routinely sending a second message. Telegram bot delivery needs your bot to have permission to send to the chosen chat.

## 4 Give Retell an HTTPS backend address

Retell needs a public HTTPS URL; localhost alone cannot receive its tool calls or webhooks.

For a supervised demonstration, use an official HTTPS tunnel such as ngrok or Cloudflare Tunnel to local port 8765. If using ngrok, after its account setup the command is:

```sh
ngrok http 8765
```

Set PUBLIC_BASE_URL in `.env` to the resulting HTTPS address. Keep both backend and tunnel running during testing. A temporary URL may change after restart; then update the Retell configuration as well.

Alternatively deploy the Dockerfile to a single-instance container host with HTTPS. Set HOST=0.0.0.0, PORT to the host's listening port, all required credentials as environment secrets, and mount persistent storage at `/app/runtime` writable by the container user. Do not upload your local `.env`. The backend must remain reachable throughout Alex's test.

The HTML shell and /health are public; all call-data API routes require DASHBOARD_TOKEN. Tools require Retell signatures and TOOL_TOKEN. Never expose a server with missing secrets or remove authentication to simplify a demo.

## 5 Select the female voice

List available female voices:

```sh
python3 configure.py voices
```

Listen to current previews in Retell and compare at least three American-English female voices using the same short scripts in ACCEPTANCE_TESTS.md. Set RETELL_VOICE_ID to the winner. The supplied speed 0.97 and turn-taking settings are a starting point; they have not been acoustically validated.

## 6 Create the Retell agent

With PUBLIC_BASE_URL, TOOL_TOKEN, RETELL_API_KEY, and RETELL_VOICE_ID set:

```sh
python3 configure.py create
```

This creates one response engine and one voice agent in your account. It prints the agent ID, which you save as RETELL_AGENT_ID in `.env`. If creation partly fails, `runtime/retell-created.json` records the created LLM ID so it can be reused rather than recreated blindly. The script intentionally stops if that marker already exists; inspect/reuse existing resources in the dashboard.

The sanitized files in `agent/` are API request templates for review. They are not Retell dashboard import/export bundles. Do not claim they have been imported or validated by Retell until setup succeeds.

If configuring manually in the dashboard:

- Paste agent/prompt.md as the prompt and use the supplied greeting.
- Add three custom functions using the definitions in retell-llm.template.json.
- Set each HTTPS URL and Authorization header locally.
- Keep args nested under args so the request includes Retell's trusted call object.
- Enable end_call.
- Configure webhook URL `/webhooks/retell` and events call_ended/call_analyzed.
- Add the post-call extraction fields from retell-agent.template.json.
- Select the same female voice and starting speech settings.

## 7 Run live tests

Use Retell's browser audio test on the agent page. Authorize microphone access yourself. Test ordinary paid service, LG/Samsung/GE warranty, a home warranty representative, and spam. Then run the edge cases in ACCEPTANCE_TESTS.md.

For standard calls, inspect the actual custom-function payload to confirm it includes transcript_object or an Agent:/User: transcript with the $99 statement and the caller's agreement after prepare_booking. The server rejects standard bookings without this evidence. If the provider changes payload format, adapt the parser rather than weakening the consent check.

Verify notification delivery on an actual call, the update after call analysis, and that a repeated webhook does not create a second database booking. Save actual call IDs and short evidence notes in LIVE_TEST_RESULTS.md.

A transcript-only playground test is useful for routing but cannot establish voice naturalness or live webhook delivery.

## 8 Reviewer access

Provide the published/testable Retell agent link or inbound number available in your account, the test window during which the backend is running, and a read-only demonstration of the notification feed. Use a dedicated review key if sharing the protected feed; do not share API or bot tokens. A voice-agent dashboard configuration alone is not a working external reviewer link.

Review the current account's sharing/publishing UI rather than inventing a universal link format. If no browser-sharing option is available, use a supervised dashboard test or arrange an inbound number after confirming any cost.

Only describe the assessment as complete after the live tests and reviewer access are verified.
