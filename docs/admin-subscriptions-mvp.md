# ARIA Admin and Subscription MVP

This milestone defines the safe first version of manual subscription management.

## Current scope
- Owner-only admin access, configured with an environment secret (never commit the secret).
- SQLite order and subscription records.
- Manual card-to-card review: an order is pending until the owner confirms the transfer independently.
- Subscription expiry is checked by the server, not trusted from Android.
- No bank API integration and no claim that a screenshot proves payment.

## Required deployment configuration
Set a long random `ARIA_ADMIN_KEY` in the server environment before enabling any admin routes. Do not use the pairing code as an admin password. Do not expose the service publicly over plain HTTP; use HTTPS behind a reverse proxy and restrict admin access.

## Suggested lifecycle
1. Customer creates an order and receives an order ID.
2. Customer transfers the displayed amount and submits the transaction reference.
3. Order stays `pending_review`.
4. Owner verifies the bank account independently, then approves the order.
5. Server creates/extends the subscription and records who approved it and when.
6. Every paid API request checks the subscription expiry on the server.
7. Refunds, chargebacks, and disputed transfers require manual review.

## Status
Planning/documentation only. This document does not mean the admin panel, payment flow, or subscription enforcement is implemented. Those require API routes, database migrations, admin UI, tests, and deployment configuration.
