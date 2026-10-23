# ARIA deployment decisions and launch checklist

Updated: 2026-10-23

## Confirmed product decisions

- Payment provider: ZarinPal.
- VPN UX: an in-app tunnel using Android `VpnService`; the user must approve Android's VPN consent dialog.
- Hosting preference: a server located in Iran.
- The owner account must remain free; subscription entitlements must be checked on the server, not trusted from APK state.

## Current release gate

The latest Android CI runs on commit `9cd7cc5ec7677d7b5faf3768821f8acee34ac278` failed during Kotlin compilation. No APK artifact was produced. Do not distribute an APK until this is fixed and a successful build artifact is verified.

Run links:
- https://github.com/Miladdeljoui/ARIA/actions/runs/39929133521
- https://github.com/Miladdeljoui/ARIA/actions/runs/39929133402

## ZarinPal integration gates

1. Owner registers at https://www.zarinpal.com/ and completes the merchant onboarding required for their account.
2. Store the Merchant ID only as a server environment secret, never in Android source or the public repository.
3. Configure a public HTTPS callback URL on the Iran-hosted backend.
4. Backend creates payment requests, records a pending order, and redirects the customer to the returned authority URL.
5. Backend verifies every callback with ZarinPal before activating a subscription. Never activate from a client-side success screen or screenshot.
6. Test duplicate callbacks, cancelled payments, invalid amounts, and failed verification in sandbox before production.
7. Generate a real customer payment URL only after the merchant account is active and the backend is deployed with credentials. No real payment URL exists yet.

Suggested environment variables (names only; never commit values):
- `ZARINPAL_MERCHANT_ID`
- `ZARINPAL_SANDBOX`
- `ARIA_PUBLIC_BASE_URL`
- `ARIA_PAYMENT_CALLBACK_URL`

## In-app VPN implementation gates

1. Choose and pin a maintained VPN engine with a compatible Android integration and review its license.
2. Deploy and operate an Iran-hosted VPN endpoint and obtain a real client configuration. A server location alone does not provide a tunnel.
3. Add an Android `VpnService` consent flow, explicit connect/disconnect state, foreground notification, reconnect handling, DNS/routing policy, and error states.
4. Store user-specific credentials securely; never put shared production credentials in the APK or GitHub.
5. Test reachability and handshake before reporting “connected”. Automatic selection may choose only among configured, reachable endpoints.
6. Do not promise operation during a complete internet shutdown; no remote tunnel can work without a path to its server.

## Iran hosting and operations

- Confirm the provider, server IP, SSH access, domain, and HTTPS certificate before deployment.
- Restrict firewall ports to the required services and expose the API only over HTTPS.
- Configure backups, health checks, access logs with minimal personal data, and secret rotation.
- Do not deploy payment processing or VPN services until authentication, authorization, abuse controls, privacy notice, and operational ownership are reviewed.

## Next implementation order

1. Fix the current Android Kotlin compilation errors and obtain a green CI build.
2. Confirm access to the Iran-hosted server and a domain/HTTPS endpoint.
3. Deploy a minimal authenticated backend and health endpoint.
4. Add ZarinPal sandbox request/callback/verification, then production after merchant activation.
5. Integrate the VPN engine only after an actual endpoint and client config are available.
