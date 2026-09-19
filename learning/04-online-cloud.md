# 04 - Always-On Cloud Architecture

The project now has a cloud deployment path so the laptop is no longer required to stay powered on.

## Built

- FastAPI cloud API
- device pairing
- hashed device-token storage
- SQLite persistence
- Ollama cloud node integration
- Dockerfile
- Docker Compose

## Engineering lesson

A local assistant and an online assistant are different operating modes:

- Laptop + local Ollama = offline/local resilience.
- VPS + cloud ARIA + Ollama = always-available online service.
- Android can choose the online node when the laptop is unavailable.

## Next

Deploy the cloud node behind HTTPS and then update Android to support cloud-first with local fallback.
