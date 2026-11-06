# ARIA Architecture

## Vision

ARIA is a local-first personal AI assistant for one owner.

## Connectivity strategy

1. **Local mode**: Python core + Ollama + local model work without internet.
2. **LAN mode**: phone and laptop can communicate over the same local network.
3. **Server mode**: when internet is available, a remote server can provide heavier models, web research, backups, notifications, and remote access.
4. **Failover**: loss of internet should reduce online capabilities, not stop the local assistant.

Important limitation: an internet outage prevents remote access from outside the local network. A phone can still communicate with the laptop over LAN/Bluetooth when the devices are reachable.

## Protection model

ARIA will use explicit permission levels:

- **SAFE**: read status, answer questions, save approved notes.
- **APPROVAL**: send messages, change files, run selected commands, deploy code.
- **CRITICAL**: payments, account/security changes, destructive operations. Always require explicit confirmation.

ARIA should never silently bypass operating-system permissions or security controls.

## Device roles

- **Laptop**: primary development/core node.
- **Android companion**: voice UI, notifications, device status, local network bridge.
- **Optional server**: remote relay, heavier model, scheduled jobs, web-connected research.

## Optional agent orchestration

Paperclip may run as a separate web service for agent roles, goals, tasks, heartbeats, budgets, approvals, and execution history. It does not replace the ARIA chat/media API or provide model inference by itself.

- Android chat, memory, user access, and image/video API remain owned by ARIA.
- Paperclip agents connect to model providers through their runtime adapters; AvalAI is the first Iran-compatible provider candidate already documented by this repository.
- Paperclip must be deployed independently with persistent storage, HTTPS, authentication, and server-side secrets.
- No agent receives production credentials or unrestricted filesystem/deployment access by default. Sensitive operations require owner approval.

Implementation status: documented integration path only. Hosting Paperclip, verifying the AvalAI adapter, and adding an authenticated in-app entry point are separate tasks.

## Future capabilities

- Persian voice conversation
- wake/attention system with battery-aware settings
- local memory and RAG
- web research when online
- safe tool calling
- code execution inside a sandbox
- security monitoring for the owner's devices
- phone notifications and approved calls

Android background execution and calling are governed by Android's permission and Telecom/foreground-service rules, so those capabilities must be implemented as a normal user-authorized app rather than a hidden background process.
