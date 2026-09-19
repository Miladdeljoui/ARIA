# ARIA Cloud Deployment

Use a Linux VPS, not shared Django hosting, for the Docker-based always-online node.

## Minimum

- Ubuntu or another supported Linux distribution
- 4 GB RAM minimum, 8 GB preferred
- 2 CPU cores minimum
- public IP
- domain for HTTPS
- Docker

## Iran-aware network fallback

Liara provides a mirrors page that can be used as a dependency/download fallback where an appropriate artifact is officially mirrored:

https://liara.ir/mirrors/

Mirror availability changes, so test the exact package or artifact before relying on it.

## Deploy

    apt update
    apt install -y docker.io docker-compose-plugin git
    git clone https://github.com/Miladdeljoui/ARIA.git /opt/aria
    cd /opt/aria/cloud
    cp .env.example .env

Set ARIA_DOMAIN and a long random ARIA_PAIRING_CODE in .env. Never commit .env.

Then:

    chmod +x deploy-ubuntu.sh
    ./deploy-ubuntu.sh

Point the domain DNS record to the VPS IP. Caddy handles HTTPS on ports 80/443. Keep 8000 and 11434 private.

After startup, download the configured model:

    docker exec -it aria-ollama ollama pull qwen3:1.7b

## Android

The app does not require Firebase, Google Sign-In or Google Maps at runtime. AndroidX dependencies still need to be resolved during build. The repository includes GitHub Actions as a second build path.

## Revenue

The first commercial layer is an AI-assisted service bot/web panel. Payment integration remains modular until the official API and credentials of an Iran-supported payment provider are available. Telegram's Bot API is HTTPS-based.

Use only supported services and official access paths. Do not build around bypassing sanctions, account restrictions, or access controls.
