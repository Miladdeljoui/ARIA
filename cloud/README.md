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

For an existing Weblines deployment, set environment variables in the Weblines console and redeploy the connected Git repository. I cannot modify private hosting secrets from the repository connector alone, so this last step requires access to the hosting account.

For a new VPS, the API proxy alone can run on a small instance because inference runs at OpenRouter, not on the VPS. Start with at least 1 vCPU, 1 GB RAM and 20 GB SSD for a light beta; add HTTPS via a domain and reverse proxy. Do not deploy Ollama on that small VPS unless you have verified its RAM/GPU needs. A local LLM needs much more memory and is a different cost profile.

Example container deployment:

```bash
cd cloud
cp .env.example .env
# Edit .env locally; never commit the populated .env
docker compose up -d --build
```

Check the service using `GET /status`. Never expose port 8000 directly to the public internet; use a TLS reverse proxy. Enable backups and monitor provider usage before sharing broadly.

## Important current limitations

Subscription status is a beta trial indicator only; verified user accounts and payment processing are not implemented. The endpoints do not yet charge users or reconcile payments. Do not collect money until a proper payment provider, server-side entitlement checks, abuse protection, and a privacy notice have been deployed and tested.
