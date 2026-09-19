# ARIA Cloud Deployment

Use a Linux VPS, not shared Django hosting, for the Docker-based always-online node.

KelonCloud currently lists Iran VPS plans including 4 GB RAM / 3 CPU and 8 GB RAM / 4 CPU options. Its Django hosting page says SSH is not provided, so the Django host is not suitable for the current Docker deployment. Provider prices and availability can change. citeturn912713search0turn856510view0

## Minimum

- Ubuntu or another supported Linux distribution
- 4 GB RAM minimum, 8 GB preferred
- 2 CPU cores minimum
- public IP
- domain for HTTPS
- Docker

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

The app does not require Firebase, Google Sign-In or Google Maps at runtime. AndroidX dependencies still come from Google's Maven repository, so initial Gradle resolution needs access to that repository. GitHub Actions is included as a second build path.

Current official Android documentation lists Android Studio Quail 4 2026.1.4 Patch 1 and AGP 9.4.0 as stable. AGP 9.4 uses Gradle 9.6.0 and JDK 17. citeturn321582search1turn321582search7

## Revenue

The first commercial layer is an AI-assisted service bot/web panel. Payment integration remains modular until the official API and credentials of an Iran-supported payment provider are available. Telegram's Bot API is HTTPS-based and supports messaging such as sendMessage. citeturn954509search0

Use only supported services and official access paths. Do not build around bypassing sanctions, account restrictions, or access controls.
