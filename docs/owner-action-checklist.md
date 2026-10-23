# ARIA Owner Action Checklist

This checklist records owner-side actions needed before ARIA can be deployed and distributed safely. Never paste secrets into chat, GitHub issues, source files, or the Android app.

## Current owner-side blockers

- [ ] Restore access to the Weblines hosting panel or choose an alternative host.
- [ ] Create Google OAuth credentials for Android sign-in and server-side ID-token verification.
- [ ] Keep Zarinpal in sandbox mode until request/verification endpoints and tests are complete.
- [ ] Create and securely back up a stable Android release-signing key before publishing any release APK.

## 1. Hosting

When panel access is restored:

1. Confirm the service/hosting project that serves `https://aria-2.weblines.ir`.
2. Confirm Python version support and persistent storage for the SQLite database, or select a managed database.
3. Configure environment variables in the provider's secret settings, not in Git:
   - `ARIA_PAIRING_CODE`: a long random secret, at least 32 characters.
   - `ARIA_OWNER_EMAIL=miladdeljoui22@gmail.com`
   - `ARIA_TRIAL_DAYS=30`
   - `ARIA_MONTHLY_PRICE_TOMAN=99000`
   - `ARIA_PUBLIC_BASE_URL=https://aria-2.weblines.ir`
   - `ARIA_GOOGLE_CLIENT_ID`: only after OAuth setup.
   - `ARIA_API_BASE_URL` and `ARIA_API_KEY`: only if using a hosted OpenAI-compatible model.
   - `ZARINPAL_SANDBOX=true`
4. Deploy only after CI tests pass, then check `/status` and a real authenticated request.
5. Verify database persistence across service restarts. Do not use ephemeral disk for the subscription database.

## 2. Google OAuth

1. Open Google Cloud Console and create/select a project.
2. Configure the OAuth consent screen and authorized app details.
3. Create the appropriate OAuth client(s) for Android and server/web verification.
4. Record the client IDs in the hosting settings. Never commit a client secret.
5. Provide the Android package name `com.miladdeljoui.aria` and the correct signing certificate SHA-1 when requested by Google.
6. Test both a verified owner identity and a different account. The owner must only receive permanent exemption after the backend validates the ID token and exact email match.

## 3. Zarinpal sandbox

1. Keep sandbox mode enabled.
2. Add sandbox credentials only to host secret settings.
3. Implement server-side payment request and verification before enabling paid access.
4. Test success, cancellation, wrong amount, invalid authority, and duplicate callback cases.
5. Do not treat a browser redirect as proof of payment. Do not switch to production without explicit owner approval.

## 4. Android release signing

1. Create a release keystore locally using Android Studio or `keytool`.
2. Back up the keystore and passwords in a secure password manager and a separate safe location.
3. Never upload the keystore or passwords to GitHub or paste them into chat.
4. Configure GitHub Actions secrets only after the key is safely backed up.
5. Build and install a signed release APK on a physical Android device before publishing it.
6. All future updates must use the same signing key.

## Safety gates

- Do not publish a release APK until signing is stable and verified.
- Do not claim Google owner exemption or paid subscription is active before backend verification is implemented and tested.
- Do not expose AI keys, pairing secrets, OAuth secrets, payment credentials, or signing material in the client app.
- Keep the free 30-day trial and 99,000 toman monthly price as product settings; enforce entitlements on the server, not only in Android UI.
