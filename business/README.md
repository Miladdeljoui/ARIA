# ARIA Revenue Layer

The revenue goal is to turn ARIA into a practical assistant for small digital services that can be sold from Iran without depending on foreign payment processors.

## First product direction

Sell AI-assisted digital services through a Telegram bot or small web panel:

- Persian content generation
- product-description writing
- CV/resume editing
- simple automation scripts
- technical support packages
- AI prompt and workflow setup
- paid access to ARIA tools

## Payment design

Use a pluggable payment-provider interface. Provider credentials stay on the server in environment variables and never enter GitHub.

The production version can connect an Iranian payment provider after its official API credentials and current API documentation are supplied.

## Automation policy

ARIA may:
- answer customers
- generate drafts
- calculate service prices from configured rules
- create invoices/orders
- notify the owner
- prepare delivery files

ARIA should ask the owner before:
- issuing refunds
- changing prices outside configured rules
- making payments
- deleting customer data
- sending sensitive or irreversible external messages

## Iran-aware engineering

The project avoids hard dependencies on Google sign-in, Firebase, Google Maps, or foreign payment processors.

The Android app uses standard Android/AndroidX libraries and the runtime assistant can operate against the owner's own server.

For services affected by regional availability, use supported local providers or a service's official documented access path. Do not build the system around bypassing sanctions, account restrictions, or access controls.
