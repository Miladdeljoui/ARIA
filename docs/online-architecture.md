# Online Deployment Plan

## Target behavior

ARIA will use a **cloud server as its always-available hub**.

    Android phone
          │
          │ HTTPS
          ▼
      ARIA Cloud
       /      \
      /        \
Laptop        AI/Tools
(local)       (online)

### Operating modes

**Online**
- Android can reach ARIA while the laptop is off.
- Cloud services can provide web-connected research, notifications and heavier AI.
- Laptop can connect to the same account when it is online.

**Internet unavailable**
- Laptop can continue local ARIA + Ollama.
- Android can continue local functions when it has another path to the laptop.
- Cloud-only functions are unavailable until connectivity returns.

## Server requirements

The next deployment requires:
- Linux VPS with a public IP
- HTTPS domain or secure tunnel
- Docker
- persistent storage
- firewall
- secret environment variables
- backups

Do not expose the current plain HTTP LAN server directly to the public internet.

## Security model

The public API will require:
- device tokens
- hashed token storage
- HTTPS
- rate limiting
- restricted admin endpoints
- owner approval for sensitive actions
- no secrets committed to Git

## AI model strategy

The cloud hub should not force the laptop to run a large model.

- local laptop: Qwen3 1.7B for offline fallback
- cloud: a stronger model or remotely hosted inference when available
- ARIA Core decides which backend is available

## Next implementation milestones

1. Cloud API
2. HTTPS deployment
3. Android online endpoint + local fallback
4. Persistent memory
5. Permission engine
6. voice conversation
7. news/threat monitoring
8. security monitoring
