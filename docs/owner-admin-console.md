# ARIA Owner Admin Console

## Owner identity and access policy

The only designated owner identity is:
- Email: miladdeljoui22@gmail.com
- Phone: 09195820148

These values identify the intended owner but are NOT passwords or proof of identity by themselves. Never grant administrator access just because a request contains this email or phone number. Before public deployment, require a strong server-side admin secret and preferably a one-time code delivered through a verified channel or a proper identity provider. Keep secrets out of GitHub, Android source code, URLs, logs, and this document.

The owner must have full access to the administration features. The owner account should be exempt from paid subscription checks, using a server-side owner role, never a client-side toggle. Do not allow ordinary users to set their own role.

## Owner console requirements

1. **Overview:** total registered accounts, active subscriptions, pending orders, revenue recorded from owner-verified payments, recent activity, API health, server uptime, CPU/RAM/disk use where available, model/backend status and error counts.
2. **Users:** search, view account and subscription status, suspend/reactivate accounts, revoke sessions, inspect support history, and grant/revoke subscription access with an audit trail.
3. **Orders and manual transfers:** order ID, user ID, plan, amount, creation time, transaction reference, proof attachment metadata, pending/approved/rejected/refunded status. Owner manually verifies the actual bank credit independently before approval.
4. **Subscriptions and plans:** create/edit plans, trial periods, start/end dates, extend/cancel subscriptions, and show expiry.
5. **App analytics:** installation/first launch counts only when the app reports them and users receive an appropriate privacy notice; active users, daily/monthly active users, app version distribution, crash/error reports and API usage. Downloads from an APK link are not the same as confirmed installs. Avoid collecting unnecessary personal data.
6. **Server and AI:** backend status, Ollama/model availability, response latency, request/error totals, safe log excerpts and resource usage. Never expose tokens, payment credentials, private prompts or full secrets in the dashboard.
7. **Owner-only access:** enforce authorization on every admin API route. UI hiding is not security. Record sensitive actions in an append-only audit log.
8. **Owner free access:** the owner role bypasses paid subscription checks server-side. All other users are subject to the subscription rules.
9. **Safety:** HTTPS only in production; rate limits; CSRF protection for cookie sessions; secure, HttpOnly, SameSite cookies; password/secret rotation; backups; data retention and account deletion procedures.

## Important implementation boundary

This document specifies the required behavior; it does not mean those features are already implemented. The current ARIA prototype's /pair and /chat endpoints do not constitute a production billing or administrator system. Before selling subscriptions, implement and test the database, authentication, admin APIs, dashboard, expiry enforcement, backups, monitoring, and deployment security. Never store a bank password or card PIN.
