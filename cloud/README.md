# ARIA Cloud

ARIA's FastAPI gateway separates Android clients from model-provider secrets. The Android APK must never contain an OpenRouter key.

## What works in this beta

- Anonymous guest registration via `POST /guest`; there is no six-digit pairing code.
- Authenticated chat via `POST /chat`, with per-device and global daily limits.
- In-app feedback via `POST /feedback`.
- Optional image/video proxy endpoints via OpenRouter. These are **disabled by default** because generation can incur real provider charges.
- The guest endpoint creates a per-install token. The server stores only a SHA-256 hash of that token.

## Free text chat through OpenRouter

OpenRouter is a unified API/catalog for many model providers. The server defaults to the dynamic `openrouter/free` chat router when `ARIA_API_KEY` or `OPENROUTER_API_KEY` is configured. Free routing has provider availability/rate limits and is not a guaranteed unlimited production service. ARIA limits guests to 10 chat requests per rolling 24 hours and the whole deployment to 45 requests per rolling 24 hours.

1. Create an OpenRouter account and API key at https://openrouter.ai/keys.
2. In your hosting provider's **private environment/secrets settings**, set `ARIA_API_KEY` to that key. Do not put a real key in GitHub, the APK, or a public issue.
3. Keep `ARIA_API_BASE_URL=https://openrouter.ai/api/v1/chat/completions`.
4. Leave `ARIA_MODEL` at the default if you want ARIA to select `openrouter/free`.
5. Redeploy/restart the cloud API and check `GET /status`. It should report `cloud_ai_configured: true`.

If the hosting runtime does not have the new `/guest` route, the APK cannot register automatically until the backend is redeployed from this repository.

## Image and video generation

OpenRouter's image API is `POST https://openrouter.ai/api/v1/images`; video generation uses asynchronous jobs at `POST https://openrouter.ai/api/v1/videos`. The current ARIA endpoints are:

- `POST /media/image`
- `POST /media/video`
- `GET /media/video/{job_id}`

These requests can consume paid credits. The app shows an explicit note before generation, and ARIA refuses media requests unless all of the following are true: the server has a provider key, `ARIA_MEDIA_ENABLED=true`, and the guest/device/global limits have not been reached. Per device, ARIA allows at most 3 images and 1 video per 24 hours; global caps are 30 images and 8 videos per 24 hours. These limits are a guardrail, not a spending guarantee. Set a provider budget and keep media disabled until you are ready to pay those costs.

Configure these server secrets/settings only after deciding how media costs will be funded:

```dotenv
ARIA_API_KEY=...                 # secret; never commit this
ARIA_MEDIA_ENABLED=true
ARIA_IMAGE_MODEL=bytedance-seed/seedream-4.5
ARIA_VIDEO_MODEL=bytedance/seedance-2.0
```

Model IDs and provider prices can change, so check the OpenRouter model catalogue/pricing before enabling media. Video models are paid in general; do not advertise image/video as free.

## Deployment

### Recommended lowest-cost deployment

**Recommended first try:** keep the existing Weblines app if you still control it. In its Environment settings, add `ARIA_API_KEY` (keep its value secret), and set `ARIA_API_BASE_URL=https://openrouter.ai/api/v1/chat/completions`. Leave `ARIA_MEDIA_ENABLED=false` to prevent surprise generation costs, then redeploy the app from this repository. After it is redeployed, check `https://YOUR-ARIA-DOMAIN/status` and confirm that `cloud_ai_configured` is `true`. Do not assume the old domain is updated merely because GitHub changed.

If you prefer a foreign VPS, a light API proxy needs no GPU because inference happens at OpenRouter. One current low-cost example is Cherry Servers Cloud VPS 1 in Frankfurt, advertised around $3.51/month in the current catalog; confirm currency, VAT and the checkout total before ordering. A comparable official Hetzner CX23 listing in Germany is €6.49/month excluding IPv4 under the price table updated in June 2026, with VAT/IP charges potentially added. This small VPS is only for the API proxy, **not** a local model. See [Cherry Servers pricing](https://www.cherryservers.com/pricing) and [Hetzner price list](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/).

For a lightweight VPS, use the dedicated `docker-compose.remote.yml`, which deliberately omits Ollama:

```bash
cd cloud
cp .env.example .env
# Edit .env locally. Set ARIA_DOMAIN to a subdomain whose DNS A record
# points at your VPS. Put ARIA_API_KEY in .env only on the private server.
# Never commit the real .env, expose the key, or put it in the APK.
docker compose -f docker-compose.remote.yml up -d --build
```

Before running the command, open the VPS firewall for TCP ports 80 and 443, point the domain's DNS A record to the VPS IPv4 address, replace `ARIA_DOMAIN=api.example.com` with your actual domain, and configure `ARIA_API_KEY`. Caddy will manage HTTPS for a valid domain. Do not expose port 8000 publicly.

### Verify deployment

1. Open `https://YOUR-ARIA-DOMAIN/status`. Check `cloud_ai_configured: true` and `anonymous_guest_access: true`.
2. Open the app. It should automatically call `POST /guest`; no six-digit code is needed.
3. Send a short Persian chat prompt. If that succeeds, text chat is connected.
4. Leave media disabled until you intentionally top up OpenRouter credits and review model pricing. Set `ARIA_MEDIA_ENABLED=true` only then. Image generation currently checks that the OpenRouter credit balance is above its API minimum; free text-chat access does not make images or video free.

Never expose port 8000 directly to the public internet. Enable persistent storage, backups and provider usage monitoring before sharing the app widely.

## Important current limitations

Subscription status is a beta trial indicator only; verified user accounts and payment processing are not implemented. The endpoints do not yet charge users or reconcile payments. Do not collect money until a proper payment provider, server-side entitlement checks, abuse protection, and a privacy notice have been deployed and tested.
