# Render deployment

Deployment is prepared, not yet performed. No cloud account or payment has been authorized.

Put the clean project source in a dedicated private repository, with render.yaml at its root. Never push .env or runtime. In Render select New > Blueprint and connect that repository. Review Starter service and 1 GB persistent disk charges before creation. Free instances sleep and cannot retain this SQLite database through a persistent disk.

Enter RETELL_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID and TOOL_TOKEN privately in Render's environment controls, using the existing local values. Render generates a separate DASHBOARD_TOKEN. Do not copy the whole local .env: HOST and PORT must use the hosting values. Run one instance only.

After deployment verify /health, then verify /api/calls returns 401 without authorization. Confirm the persistent runtime directory is writable. Update the existing Retell draft tools and webhook to the new HTTPS address, preserving TOOL_TOKEN. Publish that updated draft and select that version for the shared Voice Orb; changing the draft alone does not prove the shared published version changed.

Complete a shared-link call; verify booking/message and actual Telegram receipt. Restart the hosted service and verify prior records persist. Only then stop the local backend and tunnel. The hosted database begins empty; do not upload historical local call data automatically. Existing local pending messages remain on the local outbox.

Hosting removes the laptop dependency; Telegram reachability and delivery must still be tested from that host rather than assumed.
