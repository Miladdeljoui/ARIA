# ARIA product roadmap: public app, subscriptions, voice, ideas, and resilient connectivity

Status: **planned specification, not yet implemented in production**. Prices and payment details below are proposals and must be confirmed before charging anyone.

## Product goals

1. Publish an installable Android APK through a stable public download/release page.
2. Offer a one-month free trial for new accounts, then subscription plans.
3. Keep the owner's private ARIA controls and user-management console separate from ordinary member accounts.
4. Support Persian text chat, speech input, Persian text-to-speech, and explicit user consent for microphone use.
5. Collect user ideas and bug reports, let the owner review them, and notify users when a new version is available.
6. Prefer local/offline capability when internet routes fail, with transparent status indicators and safe fallback.

## Proposed subscription tiers (owner confirmation required)

Currency: Iranian toman per month.

| Plan | Proposed monthly price | Proposed positioning |
|---|---:|---|
| Pro | 1,500,000 toman | Standard hosted assistant, chat, voice, basic memory and idea submissions |
| Plus | 5,500,000 toman | Higher usage limits, expanded memory and priority access |
| Plus Pro | 10,000,000 toman | Highest limits and priority features, subject to published fair-use limits |

These are draft prices, not active offers. Do not collect money until terms, usage limits, cancellation, support, privacy, trial eligibility, and refund rules are published. A free first month requires account-based trial eligibility and server-side subscription timestamps so users cannot reset the trial by reinstalling the app.

## Payment and owner approval

- Preferred flow: a legitimate payment gateway with server-to-server signed callback and a verified transaction ID.
- If Blue Bank transfer is used, a receipt image alone is **not proof of payment**. Require a bank statement/API or manual review against the actual incoming transaction, amount, date, reference number, and payer details. Keep an audit log.
- The owner console can show pending payments, verified transactions, plan, trial end, subscription expiry, and actions to approve/reject after verification.
- Never ask users to send card PIN, CVV2, password, one-time password, or full banking credentials.
- Do not store unnecessary bank details or publish receipt images. Restrict access to the owner and define retention/deletion rules.
- Payment integration must use provider documentation and lawful merchant onboarding. Do not automate acceptance based only on OCR or an uploaded screenshot.

## Owner console and user management

Owner-only, authenticated dashboard:
- User list with pseudonymous account ID, plan, trial status, expiry, last activity, and moderation status.
- Payment queue: pending / verified / rejected, with evidence and audit trail access restricted to the owner.
- Approve or reject only after independent verification.
- Suspend or restore access, reset a trial only with a logged reason, and view system health.
- Require a second confirmation for financial or destructive actions. Do not expose owner endpoints or admin keys in the APK.

## Ideas and feedback

- In-app menu: **ایده برای ARIA**, **گزارش خطا**, **درخواست قابلیت**.
- Fields: short title, description, optional category, optional contact consent. Avoid collecting sensitive data by default.
- Server stores a ticket ID, created time, status, and owner response. User can see status: received / reviewing / planned / completed / declined.
- Owner receives a notification only through a configured secure channel. Do not restart any previously cancelled daily-report automation.
- Ideas must be reviewed; they should not automatically change code or deploy to users.

## Updates and public installation

- Publish signed release APKs and release notes on a stable public GitHub Releases page, then place that URL in the app and Telegram announcement.
- GitHub Actions artifacts are temporary build outputs, not a permanent public app store. A successful build must be verified before publishing.
- The app checks for a newer release when online, shows version/changelog, and links to the official release. Android generally requires the user to confirm installation; the app must not silently install updates.
- Provide SHA-256 checksums and keep release signing keys private. Never put signing secrets in GitHub source.
- A public install link does not mean the app has been security-audited or is ready for paying customers.

## Voice and accessibility

- Persian text-to-speech should read assistant replies aloud with a visible speak/stop control and speech-rate setting.
- Speech input should be tap-to-talk with a clear microphone indicator, permission explanation, cancel control, and text-edit step before sending.
- Android's standard speech recognizer may send audio to a remote provider and may not work offline. Offline speech requires a tested on-device speech model and a model size/performance check.
- Always show a text alternative and a way to disable voice.

## Connectivity and offline strategy

ARIA cannot promise uninterrupted service if all routes and local networks are unavailable. Implement explicit modes:
1. **Local mode:** Android connects to the user's laptop on the same Wi-Fi/LAN, using local Ollama/model. Can work without internet after setup.
2. **Domestic-host mode:** connect to a legally operated in-country server only when the domestic route and server are reachable. Hosting inside a country does not guarantee service during every network outage.
3. **Cloud mode:** connect to an external VPS/API when international access is available.
4. **Offline phone mode:** small on-device model and local speech assets, if supported by device memory and storage.

The client should show which mode is active and why fallback failed. Never silently route private conversations to another provider. Ask for consent before enabling cloud processing, and let users clear local history. Keep the owner model and ordinary user data separated.

## Security and privacy release gates

Before paid/public launch:
- HTTPS, authenticated APIs, rate limits, input validation, secure secret storage, account isolation, and database backups.
- No admin password, bot token, bank credentials, or signing key in Android resources or public repository.
- Payment verification server-side, audit logs, refund/cancellation process, privacy notice, data deletion route, and abuse handling.
- Threat-model review and tests for authorization, trial bypass, duplicate callbacks, account isolation, and offline behavior.
- Test on real Android devices and low-memory devices; do not describe the product as fully autonomous or as learning everything automatically.

## Implementation sequence

1. Get the Android build green and verify APK installation.
2. Publish a signed test release and stable public download page.
3. Add user accounts and server-side free-trial state.
4. Add owner-only user/subscription dashboard.
5. Integrate one verified payment provider; add Blue Bank manual reconciliation only if needed and supported safely.
6. Add ideas/bug reports and owner review queue.
7. Add release checker and opt-in update notifications.
8. Improve Persian TTS and test offline speech options.
9. Implement LAN/local mode and a tested domestic-host fallback; publish honest connectivity limitations.
10. Run security and privacy review before accepting real payments.

## Owner decisions needed before launch

- Confirm tier names and monthly prices.
- Confirm whether the free trial is exactly 30 days and whether it requires a payment method.
- Choose a legitimate payment gateway or define the manual bank-reconciliation process.
- Decide whether user accounts require phone/email or can use passkeys/anonymous IDs.
- Publish terms, privacy, cancellation, support, and refund policy.


## Confirmed beta settings (2026-10-23)

The owner confirmed these settings; they replace the proposed price/trial values above for the beta plan:

- Owner email: `miladdeljoui22@gmail.com`, free forever only after server-verified Google sign-in.
- Everyone else: 30-day free trial during the public beta.
- Monthly price after trial: 99,000 toman (990,000 rial when calling Zarinpal endpoints that expect rial).
- Payment starts in Zarinpal sandbox, with server-side verification before subscription activation.
- Distribution: GitHub Releases.
- In-app feedback: users can submit bug reports, suggestions and ratings; reports should be stored server-side for owner review.

These settings are recorded, but are **not implemented merely by appearing in this document**. Required work: verify Google ID tokens, enforce trials on the server, store accounts/subscriptions/payments, implement Zarinpal request and verification callbacks idempotently, add feedback endpoints and UI, add GitHub Release update checking, then build and test the APK. Do not embed secrets in Android or commit real credentials.
