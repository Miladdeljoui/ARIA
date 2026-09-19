# 05 - Iran-aware deployment strategy

## Goal

Keep the project usable despite regional availability and connectivity problems.

### Android

- No Firebase dependency.
- No Google Sign-In dependency.
- No Maps dependency.
- Local Text-to-Speech.
- Cloud endpoint configurable by the owner.
- Laptop fallback remains available.

### Cloud

- Linux VPS
- Docker
- HTTPS via Caddy
- SQLite for the first persistent prototype
- Secrets supplied through environment variables

### Income

The first revenue direction is a Telegram/web service layer around AI-assisted digital services. Payment providers are modular so an Iranian provider can be added after the owner supplies an official API integration.

Telegram's Bot API is an HTTPS API and supports methods such as getMe and sendMessage, which is enough for the first bot layer. citeturn954509search0

### Portfolio

Each real implementation step is committed to GitHub with a clear commit message so employers can see progression instead of a single polished demo.
