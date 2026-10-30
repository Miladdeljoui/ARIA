# ARIA Cloud

ARIA's FastAPI gateway keeps model-provider credentials on the server. The Android APK never receives API secrets. The Android guest flow uses `POST /guest` and does not require a six-digit pairing code.

## Iran-compatible multi-model gateways

### Recommended first trial: AvalAI

AvalAI publishes an OpenAI-compatible API at `https://api.avalai.ir/v1`. Its official pricing page advertises up to **200,000 toman of free API credit for new users**: 25,000 toman after email registration, and a top-up to 200,000 toman total after phone verification. This is a trial credit, not an unlimited free plan. Verify eligibility and the real balance on the developer dashboard before relying on it.

The provider's documentation lists hundreds of models from multiple companies, a live public model/pricing catalogue, chat completions, image generation, and a separate video API section. Chat/image APIs are implemented as ARIA server-side adapters below. Do not assume every video route or model is enabled for every account; inspect the current catalogue and test with a small budget.

Create an API key at https://chat.avalai.ir/ and configure on the VPS only:

```dotenv
ARIA_PROVIDER=avalai
ARIA_API_BASE_URL=https://api.avalai.ir/v1/chat/completions
ARIA_API_KEY=YOUR_AVALAI_API_KEY
ARIA_MODEL=gpt-5.4-nano

ARIA_IMAGE_API_URL=https://api.avalai.ir/v1/images/generations
ARIA_IMAGE_MODEL=gpt-image-2.5-flare
ARIA_IMAGE_API_KEY=

ARIA_MEDIA_ENABLED=false
```

Leave `ARIA_IMAGE_API_KEY` blank to reuse the text API key. The API requires a Bearer key. ARIA's chat adapter uses the configured OpenAI-compatible chat-completions endpoint; the image adapter sends an OpenAI-style image-generation request and expects Base64 image data or an image URL.

Official docs:
- API overview and base URL: https://docs.avalai.org/en/api-reference/introduction
- Image generation: https://docs.avalai.org/fa/api-reference/images
- Video API section: https://docs.avalai.org/en/api-reference/videos
- Pricing and signup credit: https://docs.avalai.org/en/pricing
- Public live model catalogue: https://api.avalai.ir/public/models

### HeroAI: one gateway with an Iran-access mirror

HeroAI's official API reference documents one Bearer virtual key and an OpenAI-compatible gateway for several providers. It explicitly documents an Iran mirror: `https://iranapi.heroai.ir/ai` (or `/v1`). Its reference lists chat completions, image generation, and video generation endpoints. This may be the closest fit to a single provider for all three ARIA modes. I could not verify a public price list from its API reference, so check the dashboard price and model availability before adding credit.

Chat gateway example:

```dotenv
ARIA_PROVIDER=heroai
ARIA_API_BASE_URL=https://iranapi.heroai.ir/ai/chat/completions
ARIA_API_KEY=YOUR_HEROAI_VIRTUAL_KEY
ARIA_MODEL=deepseek/deepseek-chat
```

HeroAI image and video endpoints also exist, but ARIA's current media adapters are AvalAI/Doona style for images and Pollinations for video. Do not switch the image/video route to HeroAI until its exact request schema, response shape, video polling, price, and Iran-mirror connectivity have been tested.

Official reference: https://api.heroai.ir/docs

### Other alternatives

**1xAi** provides a local Toman-based API gateway and model catalogue. The documented OpenAI-compatible chat endpoint is `https://1xai.ir/v1/chat/completions`. Its API wallet is separate from its consumer chat free plan; do not assume the web chat allowance covers API requests.

```dotenv
ARIA_PROVIDER=1xai
ARIA_API_BASE_URL=https://1xai.ir/v1/chat/completions
ARIA_API_KEY=YOUR_1XAI_API_KEY
ARIA_MODEL=deepseek-chat
```

Official docs: https://1xai.ir/docs

**Doona** provides an OpenAI-compatible API and image generation through `https://platform.doona.ai/v1`. It is another local/Toman billing option.

```dotenv
ARIA_PROVIDER=doona
ARIA_API_BASE_URL=https://platform.doona.ai/v1/chat/completions
ARIA_API_KEY=YOUR_DOONA_API_KEY
ARIA_MODEL=gemini-3.5-flash-lite
ARIA_IMAGE_API_URL=https://platform.doona.ai/v1/images/generations
ARIA_IMAGE_MODEL=gpt-image-2
```

Official docs: https://platform.doona.ai/docs

## Video generation

ARIA's current video adapter uses Pollinations from the **server**, not from Android. It needs a server-side `sk_` generation key:

```dotenv
POLLINATIONS_API_KEY=YOUR_POLLINATIONS_SECRET_KEY
ARIA_VIDEO_MODEL=bytedance/seedance-2.0-mini
ARIA_MEDIA_ENABLED=true
```

Never put a Pollinations `sk_` key or any other provider secret in the APK, a public GitHub commit, or an Android setting. Pollinations model availability, prices and key permissions may change. Check https://gen.pollinations.ai/docs and https://enter.pollinations.ai. Image/video generation is not automatically included in a free chat allowance.

Current app caps: up to 3 images and 1 video per device per 24 hours; global caps are 30 images and 8 videos per 24 hours. These count caps do not guarantee a spending ceiling. Configure a provider-side budget, begin with `ARIA_MEDIA_ENABLED=false`, and only enable it after checking actual prices.

## Small VPS in Iran

The VPS runs only the ARIA API gateway. Model inference and image/video processing happen at API providers, so **a GPU is not required**. One vCPU and 1 GB RAM can be enough for a personal test; consider 2 vCPU and 2 GB RAM for multiple users and file handling.

Prices seen in provider pages on 30 October 2026 (check the final checkout total, traffic, VAT, support and refund terms before paying):
- Bia2Host Iran VPS: 1 GB RAM / 1 core / 10 GB SSD from about 390,000 toman/month: https://bia2host.com/iran-vps/
- IranVM: 1 GB RAM / 1 core / 10 GB SSD around 545,000 toman/month; 2 GB / 2 core around 895,000 toman/month: https://irvm.org/pricing/

Before paying, ask the hosting provider to confirm:
1. SSH/root access and Docker support.
2. A public IPv4 address and DNS for your subdomain.
3. Outbound HTTPS access to the chosen AI provider (for example `api.avalai.ir`) and Pollinations (`gen.pollinations.ai`).
4. A test period or refund if outbound routes are blocked.
5. Persistent storage and backups for `/data/aria_cloud.db`.

A server located in Iran does not guarantee that it can reach every external provider. Test outbound HTTPS from the actual VPS before purchasing a long-term plan.

## Deploy

Point a subdomain's DNS A record at the VPS IPv4 address, open ports 80 and 443, then:

```bash
git clone https://github.com/Miladdeljoui/ARIA.git
cd ARIA/cloud
cp .env.example .env
nano .env
docker compose -f docker-compose.remote.yml up -d --build
```

Set `ARIA_DOMAIN` to your real subdomain. Enter the real API keys in `.env` on the VPS only. Caddy terminates HTTPS on port 443; do not expose port 8000 publicly.

## Verify

1. Visit `https://YOUR-DOMAIN/status`. Confirm `cloud_ai_configured: true` and `ai_provider: "avalai"` (or the provider you chose).
2. Confirm `image_enabled` and `video_enabled` only after setting the separate server-side keys and enabling media.
3. Open the app; it registers a guest token automatically.
4. Send a short Persian message in Chat mode and check the response.
5. Try one image with a small budget. Try one short video only after Pollinations is configured.

## Important limitations

- Free models and signup credit are limited by provider, account eligibility, model availability, and rate limits. No API provider guarantees unlimited free access.
- Render's free service may sleep after idle time and its temporary filesystem is not durable; use it for experiments, not long-lived public user data.
- ARIA currently limits guests to 10 chat requests per rolling 24 hours and the deployment to 45 per rolling 24 hours.
- Subscriptions and payments remain beta placeholders. Do not collect money until account identity, payment verification, entitlement, data backups, privacy and refunds have been implemented and tested.
- Prompts are sent from ARIA's server to the configured provider. Do not send passwords, card details, or other sensitive data.
