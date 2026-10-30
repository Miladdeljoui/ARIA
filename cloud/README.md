# ARIA Cloud

ARIA's FastAPI gateway keeps AI-provider credentials on the server. The Android APK never receives Doona, 1xAi, OpenRouter, or Pollinations secret keys.

## Current API flow

- Android creates a per-install guest session with `POST /guest`. There is no six-digit pairing code.
- Chat is sent to `POST /chat`, through the configured OpenAI-compatible gateway.
- Image generation is proxied through `POST /media/image`.
- Video generation is proxied through `POST /media/video`, using Pollinations.
- Feedback is sent to `POST /feedback`.
- The server stores a hash of the guest token, not the token itself.

## Iran-oriented text and image provider: Doona

Doona documents an OpenAI-compatible API at `https://platform.doona.ai/v1`, plus Gemini-compatible image generation and OpenAI-compatible `/images/generations`. Its pricing is pay-as-you-go; a free unlimited API is not promised.

Create an API key from the Doona dashboard, then configure these values in the server's private environment (not in GitHub or the APK):

```dotenv
ARIA_PROVIDER=doona
ARIA_API_BASE_URL=https://platform.doona.ai/v1/chat/completions
ARIA_API_KEY=YOUR_DOONA_API_KEY
ARIA_MODEL=gemini-3.5-flash-lite

ARIA_IMAGE_API_URL=https://platform.doona.ai/v1/images/generations
ARIA_IMAGE_MODEL=gpt-image-2
# Optional separate image key. Leave blank to reuse ARIA_API_KEY.
ARIA_IMAGE_API_KEY=
```

Choose a model ID from Doona's live dashboard/catalog before deploying; the example is taken from the current docs and may change. The response includes provider cost information, but ARIA currently only returns the generated image and model name in its chat UI.

Official docs: https://platform.doona.ai/docs

## Alternative Iranian-focused gateway: 1xAi

1xAi also documents an OpenAI-compatible endpoint. To use it for text chat, change:

```dotenv
ARIA_PROVIDER=1xai
ARIA_API_BASE_URL=https://1xai.ir/v1/chat/completions
ARIA_API_KEY=YOUR_1XAI_API_KEY
ARIA_MODEL=MODEL_ID_FROM_1XAI_CATALOG
```

1xAi lists many model providers and a separate web-chat free plan, but its API docs instruct users to charge the API wallet. Do not assume the free web-chat allowance also applies to API calls. Its published pricing includes an added margin over upstream provider prices.

Official docs: https://1xai.ir/docs

## Video generation through Pollinations

Video generation is a separate service from Doona's documented chat/image endpoints. Pollinations has a video endpoint and requires a secret `sk_` key for server generation. Do not use a raw `pk_` as a generation credential and never place `sk_` in the Android app.

Set these server-only values:

```dotenv
POLLINATIONS_API_KEY=YOUR_POLLINATIONS_SK_KEY
ARIA_VIDEO_MODEL=bytedance/seedance-2.0-mini
```

The API's available models, prices, and key permissions can change. Check the current model catalogue and key budget at https://gen.pollinations.ai/docs and https://enter.pollinations.ai before enabling video. Video is not free by default.

## Enable image/video only after setting a budget

Start with media disabled:

```dotenv
ARIA_MEDIA_ENABLED=false
```

After checking the API wallet, model price, and key budget, enable:

```dotenv
ARIA_MEDIA_ENABLED=true
```

Current ARIA guardrails: per device, at most 3 images and 1 video per rolling 24 hours; globally, 30 images and 8 videos per rolling 24 hours. These are request-count limits, not a spending guarantee. Set a provider-side budget too. Video output is capped at 20 MB in this API response.

## Free or low-cost chat alternative

The Android app keeps OVHcloud AI Endpoints as a fallback only. OVHcloud's official anonymous limit is 2 requests/minute per IP and model; it is not a reliable unlimited production plan, and model prices/free status must be checked in its live catalogue.

Official docs:
- https://docs.ovh.com/en/guides/public-cloud/ai-machine-learning/ai-endpoints-troubleshooting/
- https://endpoints.ai.cloud.ovh.net/

## Deployment on a small Iranian VPS

The VPS runs only the ARIA API gateway. Doona and Pollinations perform inference/generation remotely, so **a GPU is not required**. For a personal beta, 1 vCPU and 1 GB RAM may be enough; for several users and media responses, choose at least 2 vCPU and 2 GB RAM.

Example Iranian prices observed on 30 October 2026 (check checkout price, traffic, VAT, and refund terms before paying):
- Bia2Host: its published 1 GB / 1 Core / 10 GB plan starts around 390,000 toman/month: https://bia2host.com/iran-vps/
- IranVM: its listed 1 GB / 1 Core / 10 GB plan is around 545,000 toman/month; 2 GB / 2 Core is around 895,000 toman/month: https://irvm.org/pricing/

Before paying, ask the host to confirm:
1. SSH/root access and Docker support.
2. A public IPv4 address and ability to point your own domain to it.
3. Outbound HTTPS access from the VPS to `platform.doona.ai` and `gen.pollinations.ai`.
4. A test period or refund policy if those external routes are blocked.
5. Persistent storage and routine backups for `/data/aria_cloud.db`.

A domestic VPS improves the phone-to-ARIA route for users inside Iran, but it does **not** guarantee that the VPS itself can reach every external model provider. Run an outbound connectivity test before committing to a long plan.

### Install

On the VPS, point a subdomain's DNS A record at its IPv4 address, open ports 80 and 443, then:

```bash
git clone https://github.com/Miladdeljoui/ARIA.git
cd ARIA/cloud
cp .env.example .env
nano .env
docker compose -f docker-compose.remote.yml up -d --build
```

Set `ARIA_DOMAIN` to your real subdomain, and enter all API keys in `.env` on the server only. Do not expose port 8000 publicly; Caddy terminates HTTPS on 443. Protect the server and the `.env` file. For a public production service, use a managed database/backup plan and rate-limit the guest endpoint.

### Verify

1. Visit `https://YOUR-DOMAIN/status`.
2. Confirm `cloud_ai_configured: true` and `ai_provider: "doona"` (or your chosen provider).
3. Confirm `image_enabled` and `video_enabled` only when you intentionally configured each key and turned media on.
4. In the app, select Chat and send a short Persian test prompt.
5. Test one image before enabling video. Video can take several minutes and may cost more.

## Free-tier and server limitations

- Free models are subject to provider availability, throttling, and changing terms. No provider guarantees unlimited free use.
- Render's free service may sleep after idle time and its temporary filesystem is not a durable database. Use it for experiments, not long-term public user data.
- The existing API currently limits guests to 10 chat requests per rolling 24 hours and the whole deployment to 45 per rolling 24 hours.
- Subscription and payment fields remain beta placeholders. Do not charge users until identity, payment verification, access rules, backups, privacy, and refunds are implemented and tested.
- ARIA's cloud database records chat messages for usage tracking. Treat prompts as data sent to both ARIA's server and the selected provider; do not send passwords, banking credentials, or sensitive information.
