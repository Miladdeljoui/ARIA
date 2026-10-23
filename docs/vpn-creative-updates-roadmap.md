# ARIA roadmap: VPN, creative studio, chat, updates and owner access

Status: roadmap/design specification. The features below are not all implemented or ready for users yet.

## Navigation concept

Bottom navigation:
1. چت: Persian AI chat and conversation history.
2. ساخت عکس: prompt-based image generation through a configured image provider; show provider, cost and availability.
3. ساخت کلیپ: video creation through a configured provider, with generation status and clear usage limits.
4. ایده‌ها: submit an idea or bug report, view ticket status.
5. VPN: a separate, clearly labeled entry. It should offer:
   - Open the official Shir o Khorshid app/release page.
   - Open the official MahsaNG app/release page.
   - Open Tor via a separately installed trusted Tor client such as Orbot, only if the user chooses it.
   - Explain these are separate projects and ARIA does not operate or guarantee their networks.

Official sources:
- Shir o Khorshid Android releases: https://github.com/shirokhorshid/shirokhorshid-android/releases
- MahsaNG releases: https://github.com/GFW-knocker/MahsaNG/releases/latest
- MahsaNG Google Play: https://play.google.com/store/apps/details?id=com.MahsaNet.MahsaNG
- Orbot source: https://github.com/guardianproject/orbot-android

## VPN safety and technical constraints

- First iteration should link to official external apps/releases, not copy binaries or merge their code into ARIA.
- A direct in-app VPN tunnel requires Android VpnService permission, reviewed tunnel implementation, server/config discovery, latency and reachability testing, reconnect logic, and a privacy/security review.
- Do not claim ARIA can always find a working or fastest server: results vary by carrier, location, congestion and blocking. If implemented, test candidate endpoints, measure successful handshake and latency, then choose the best reachable route.
- Tor is not inherently fastest; it prioritizes anonymity and can be slower. Do not promise Tor speed.
- Before bundling or modifying third-party apps, review license, attribution, source-offer obligations, trademarks and privacy policy. MahsaNG README says its repository cannot build a standalone APK from source because some authentication/config-encryption parts are closed; do not represent a DIY build as official MahsaNG.
- Never silently route user traffic or conversation data. Explain what traffic is routed, show status, and require Android VPN consent.
- If no route is reachable, report unavailable rather than showing a fake connected status.

## Owner account: no charge for the owner

- Owner's own account should have a server-side owner role and a logged-in exemption from subscription checks.
- Never hardcode owner access in the APK alone; the server must verify the account role.
- All other accounts remain subject to published trial/plan policy.

## Chat, image and video generation

- Chat should use the configured model/server and show which backend is active.
- Image and video creation need a real provider/API, budget limits, safety handling, job queue, error handling and user-visible costs/quotas.
- Do not imply image/video generation works offline unless an on-device model has been integrated and tested.
- Allow users to save outputs and report failed generations.

## Release updates for owner and all users

- Use GitHub Releases as the stable version source.
- Add versionCode, versionName, release notes and SHA-256 checksum for each APK.
- App checks the official release feed on launch/manual refresh and shows an update banner to all accounts, including the owner.
- Clicking the banner opens the official release page. Android installation must be confirmed by the user; do not promise silent updates.
- Admin announcements can later use a properly configured push notification service after user consent.
- Never place signing keys or notification server credentials in the public repo or APK.

## Public release and subscriptions

- Publish an actual tested APK before sharing an installation link.
- Owner dashboard, trial, subscriptions, payments, ideas, image/video generation and VPN tunnel integration need separate implementation and tests.
- Payment verification must be server-side through a payment gateway or independently reconciled bank transaction. A screenshot alone is not proof.
- Proposed plans remain drafts until quotas, terms, cancellation and refunds are confirmed.
- Do not claim “the world's best AI” without independent evidence. Describe verifiable capabilities instead.

## Implementation order

1. Get a green APK build and test installation.
2. Add stable release page and update banner.
3. Build owner role and owner dashboard.
4. Build chat history and ideas submission.
5. Add voice and TTS with consent.
6. Add image generation provider and limits.
7. Add video provider and job status.
8. Add external VPN shortcuts and attribution.
9. Consider direct VPN integration only after license and security review.
10. Add real subscription/payment flows after tests and published terms.
