# ARIA Cloud

The cloud node keeps ARIA available when the laptop is turned off.

## Architecture

    Android
       |
      HTTPS
       |
    Reverse Proxy
       |
    ARIA Cloud API
       |
    Ollama
       |
    Qwen

The cloud node stores device authentication hashes and conversation records in SQLite.

## Important

Do not expose port 8000 directly to the public internet. Put the service behind an HTTPS reverse proxy and a firewall.

Before using the Compose stack, pull the configured model inside the Ollama container:

    docker exec -it aria-ollama ollama pull qwen3:1.7b

The VPS should have enough RAM/storage for the selected model and Docker workloads.

## Status

The cloud API exposes:

    GET /status

Pairing:

    POST /pair

Chat:

    POST /chat

A production deployment still needs HTTPS, rate limiting, secret rotation, backups, monitoring and a secure domain.
