# ARIA Public API deployment (initial backend milestone)

## Implemented in this milestone
- Google ID-token validation against Google's tokeninfo endpoint and configured OAuth audience.
- Session-backed identity keyed by Google subject (`sub`), not email.
- Three-day trial on first account creation.
- Referral-code creation and redemption window.
- Two-day Pro rewards for both users after an owner qualifies a pending referral.
- SQLite order records and owner-only manual bank-transfer review endpoints.
- Owner role configured only by `ARIA_OWNER_GOOGLE_SUB`.
- Basic security headers and HttpOnly/SameSite cookies.

## Not yet ready for public launch
- Production frontend, Google sign-in button, or Android sign-in integration.
- Real payment gateway checkout and verified payment callback.
- Rate limiting, full CSRF defenses, monitoring, backup automation, and production hosting.
- Complete owner dashboard UI. Owner API endpoints exist but still need a UI.
- Automated anti-fraud detection beyond basic referral checks.

## Configuration
Set these on the server, never commit them:
- `ARIA_SESSION_SECRET`: at least 32 random characters.
- `ARIA_GOOGLE_CLIENT_ID`: OAuth Web Client ID used as token audience.
- `ARIA_OWNER_GOOGLE_SUB`: stable Google `sub` claim for the owner's verified account. Do not use email or phone as this value.
- Optional `ARIA_PUBLIC_DB`: persistent writable SQLite path.
- `ARIA_COOKIE_SECURE=1`: required behind HTTPS.
- `ARIA_PUBLIC_PORT`: default 8787.

## Run locally
From repository root:

```sh
python -m pip install -r server/requirements.txt
python -m server.public_api
```

The API binds to 127.0.0.1 by default. Put it behind a trusted HTTPS reverse proxy for deployment. Do not expose Flask's development server directly to the internet.

## Endpoint summary
- `GET /api/health`
- `POST /api/auth/google` with JSON `{ "credential": "<Google ID token>" }`
- `POST /api/auth/logout`
- `GET /api/me`
- `POST /api/referrals/redeem` with JSON `{ "code": "<referral code>" }`
- `GET /api/subscription`
- `POST /api/orders` with plan, amount_minor, currency, and method
- `GET /api/admin/overview` (owner session required)
- `POST /api/admin/orders/<id>/review` (owner session required)
- `POST /api/admin/referrals/<id>/qualify` (owner session required)

The gateway method only creates a pending order; it does not grant access because payment verification is not implemented. Do not advertise online payments as working yet.
