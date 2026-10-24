# ARIA Revenue and Referral MVP

Status: product/engineering specification only. This document does not mean the features are implemented.

## Product decisions

- Audience: general users.
- AI mode: hybrid local and cloud, selected according to availability, privacy, quality, and cost.
- Payments: manual card-to-card transfer with owner review and online gateway when a suitable provider is configured.
- New-user trial: 3 days of PRO for eligible new accounts.
- Referral reward: 2 days of PRO for both the inviter and the invited user after a valid referral is verified.

## Subscription tiers

### Free
- Core text chat with a configurable usage budget.
- Basic writing, learning, and programming assistance.
- Limited memory and supported tools.
- Clear usage limits and upgrade path.

### PRO
- Higher configurable usage limits.
- Access to stronger cloud models when configured and affordable.
- Advanced voice/file/image tools only when implemented and supported.
- Expanded memory/personalization within privacy controls.
- No promise of unlimited usage; costs and quotas must be enforced server-side.

### Trial
- Three days from the server-recorded activation timestamp.
- One trial per eligible person/account according to anti-abuse policy.
- No automatic charge at trial end.
- On expiry, account returns to Free without deleting user data.

## Referral rules

1. Each account receives a unique, non-guessable referral code or link.
2. The referred person must be a genuinely new account and complete required account verification.
3. Both inviter and invitee receive 48 hours of PRO only after the server validates the referral.
4. A referral can be attributed to only one inviter.
5. Self-referrals, duplicate accounts, repeated claims, suspicious device/account patterns, and abuse are rejected or queued for review.
6. Rewards are recorded as immutable ledger events with inviter, invitee, reason, timestamps, status, and expiry.
7. The server calculates entitlement. The Android client cannot grant or extend PRO.
8. Show pending, approved, and rejected referrals and the reward history to users.
9. Define rate limits and an owner-configurable referral cap before public launch.
10. Do not collect invasive device fingerprints; use proportionate anti-abuse checks and disclose relevant data use.

## Payments

### Manual transfer
- User creates an order for a selected plan and sees the amount and payment instructions.
- User submits the transaction reference and only the minimum proof needed.
- Order status: pending, approved, rejected, or needs-information.
- Owner-only admin reviews the order.
- PRO activates only after server-side approval; every decision is audited.
- Never store card PINs, passwords, or unnecessary payment-card details.

### Online gateway
- Integrate only after selecting a provider that supports the target market.
- Verify payment callbacks server-side using the provider's signature/verification API.
- Make fulfillment idempotent so duplicate callbacks cannot grant multiple subscriptions.
- Never trust a client-side success screen as proof of payment.

## Entitlement and data model (suggested)

- users: id, verified identifiers, created_at, role, status
- plans: id, name, duration, price, currency, feature_limits, active
- orders: id, user_id, plan_id, amount, currency, method, status, reference, reviewed_by, reviewed_at
- subscriptions: id, user_id, plan_id, source, starts_at, expires_at, status
- referrals: id, inviter_user_id, invitee_user_id, code, status, created_at, verified_at
- reward_ledger: id, user_id, referral_id, reward_hours, status, created_at, expires_at
- usage_events: user_id, model, tokens_or_units, estimated_cost, created_at
- admin_audit_log: admin_id, action, target_type, target_id, created_at, metadata_redacted

Use database transactions for referral approval, reward creation, and subscription activation. Add unique constraints to prevent duplicate referral attribution and duplicate payment fulfillment.

## Owner and security requirements

- Owner role is granted only by trusted server-side configuration and verified authentication, not by email/phone alone or a client flag.
- Owner receives PRO without payment through a server-side entitlement rule.
- Admin endpoints require strong authentication, authorization on every request, rate limiting, secure sessions, CSRF protection where applicable, HTTPS in production, and audit logging.
- Secrets stay in environment variables or a secret manager, never in Git or the Android APK.
- Do not expose the local Ollama server or development API directly to the public internet.
- Provide account deletion/export and clear privacy disclosures before public release.

## Implementation phases

1. Inspect current server and Android API contracts; add tests before changing behavior.
2. Add a persistent SQLite data layer and migrations for users, plans, orders, subscriptions, referrals, reward ledger, and audit events.
3. Add server-side authentication and entitlement checks, including owner bypass and trial expiry.
4. Add referral attribution and atomic reward issuance with abuse controls.
5. Add manual-payment order lifecycle and owner review endpoints.
6. Add a private admin web interface for users, plans, orders, referrals, and service/usage health.
7. Add gateway integration only after provider selection.
8. Add Android screens for plans, trial status, invite link, referral progress, payment orders, and history.
9. Test expiry boundaries, duplicate requests, spoofed user IDs, concurrent reward claims, duplicate gateway callbacks, unauthorized admin access, and database recovery.
10. Deploy behind HTTPS with backups, monitoring, rate limits, and a documented rollback plan.

## Acceptance criteria

- Client-side requests cannot grant PRO, change role, approve payments, or extend expiry.
- Eligible new accounts receive exactly one 3-day trial.
- A verified, valid referral grants exactly 48 hours to both parties, once.
- Expired entitlements reliably fall back to Free.
- Manual orders grant PRO only after owner approval.
- Duplicate/replayed requests do not duplicate rewards or subscriptions.
- Owner access and all admin actions are auditable.
- The system reports actual implementation status accurately; planned features are not described as live.
