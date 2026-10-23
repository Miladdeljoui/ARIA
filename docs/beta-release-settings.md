# ARIA Public Beta Release Settings

Status: planned configuration. These values do not mean the features are implemented or enabled yet.

## Product settings

- Owner email: `miladdeljoui22@gmail.com`
- Owner entitlement: free forever, only after the backend verifies the Google identity token and the email matches exactly.
- Public beta: free access for every eligible user during the 30-day trial.
- Trial: 30 days from the server-recorded account creation/first activation time. The client clock must not decide entitlement.
- Monthly price after trial: 99,000 toman = 990,000 rial for Zarinpal API requests that use rial.
- Payment: Zarinpal sandbox first. Do not grant paid entitlement based on the browser redirect alone; verify authority and amount server-side and handle duplicate callbacks idempotently.
- App distribution: GitHub Releases, with in-app update checking against a published release and an explicit Android install confirmation.
- Feedback: in-app bug report, feature request, rating, app version, optional diagnostic details, and a user-visible submission confirmation. Avoid collecting passwords, tokens, payment-card details, or unnecessary personal data.

## Required server-side configuration

Set these in the hosting provider's secret/environment settings, never in the Android APK or a committed real `.env` file:

- `ARIA_OWNER_EMAIL=miladdeljoui22@gmail.com`
- `ARIA_TRIAL_DAYS=30`
- `ARIA_MONTHLY_PRICE_TOMAN=99000`
- `ZARINPAL_SANDBOX=true`
- `ZARINPAL_MERCHANT_ID=` (sandbox merchant ID)
- `ARIA_GOOGLE_CLIENT_ID=` (OAuth web/server client ID)
- `ARIA_PUBLIC_BASE_URL=https://aria-2.weblines.ir`

A real implementation also needs database-backed users, subscription and payment records, Google ID-token validation, payment request/verification endpoints, and release metadata. Never put the merchant ID, OAuth client secret, or AI API key in the Android app.

## Beta acceptance checklist

- A non-owner account receives exactly 30 trial days according to server time.
- The owner account is free indefinitely only after verified Google sign-in.
- The client cannot change its own trial expiry, email, price, or payment status.
- Payment only activates after successful server-side Zarinpal verification for the expected amount.
- Duplicate payment callbacks do not extend a subscription twice.
- Bug reports are stored server-side and can be reviewed by an authorized owner.
- Update metadata points only to a real GitHub Release asset; APK signature/update compatibility is tested.
- The APK is built and tested on a physical Android device before announcing it as ready.
