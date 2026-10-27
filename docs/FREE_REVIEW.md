# Free live review

No paid hosting, n8n subscription, or phone number is required for this browser-call demonstration. Do not create the optional Render service.

## Components

- Retell Voice Orb: the user-enabled shared link, verified to load without a login. Levon completed a successful call through it.
- Notification interface: the protected browser call feed. It polls every five seconds while open and shows stored calls, type, collected details, outcome, summary and transcript. Full analysis may arrive after call-ended details.
- Telegram: additional preferred notification channel. Actual receipt is proven, but network timeouts can delay delivery; it is not the sole review interface.

## Reviewer access

The private runtime/REVIEW_ACCESS.txt file contains the current public feed address and a separate read-only review key. Send these privately to Alex with the Voice Orb link. Do not send .env, API keys, bot tokens, tool authorization or the administrative dashboard key. The review key only permits GET access, excludes synthetic and pre-review historical calls, and cannot submit booking actions. Anyone holding it can see calls within the review window; rotate/remove REVIEW_TOKEN after review and restart the backend.

## During the agreed review window

Keep the laptop powered, lid open, internet connected, backend running and Cloudflare tunnel running. Prevent idle sleep for the window only. Stop sleep prevention when review ends. If the tunnel address changes, update Retell tools AND webhook, publish the changed version, select that version for the shared link, and repeat verification.

Alex opens the Voice Orb and the notification dashboard in two tabs. Enter the review key into the dashboard. Complete a fictional call in the Voice Orb, end it, and confirm the matching record appears in the feed. The dashboard itself is the required post-call notification interface; Telegram is supplementary. The notification feed is not a calendar: a booking handoff confirms a request, not an appointment slot.

## Readiness limits

The public page loading alone is not an end-to-end check. Before sending, verify a new shared-link call appears through the restricted reviewer dashboard. The temporary tunnel has no uptime guarantee; an agreed live window and a reachable contact are necessary. This setup does not promise round-the-clock availability. If connectivity fails, pause the review and reconnect; never claim tools succeeded when they did not.
