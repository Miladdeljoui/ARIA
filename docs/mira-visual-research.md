# ARIA visual direction: embodied assistant

## Reference research

The Instagram Reel screenshot supplied for this idea shows a neon, humanoid-style AI visual and mentions “New humanoid feature for MIRA.” The exact Reel could not be reliably identified from the screenshot alone, so this document records related public projects rather than claiming to have found the exact implementation.

Related projects reviewed:

- [Vexillon-ai/MIRA](https://github.com/Vexillon-ai/MIRA): a self-hosted personal AI agent with Telegram and other messaging channels, memory, voice, tools, and a web interface.
- [ErikMischiatti/M.I.R.A](https://github.com/ErikMischiatti/M.I.R.A): a desktop embodied-assistant prototype with expressive animated eyes, visible interaction states, modular cognition, and optional Ollama integration.
- [MIRA-Robot](https://github.com/habibulrahman636-alt/MIRA-Robot): a small hobby robotics project combining OLED expressions, servo motion, sensors, and an AI talking-assistant concept.

These are research references only. ARIA does not copy or automatically integrate their code.

## ARIA concept image

![ARIA humanoid visual concept](assets/aria-humanoid-concept.svg)

The concept uses a dark glass-like face, violet/magenta light contours, cyan eye indicators, and a clean technical HUD aesthetic. It is a design direction, not a picture of a completed physical robot.

## How this relates to ARIA

Potential future milestones:

1. Use a lightweight animated eye/face in the Android and web interfaces.
2. Display explicit states such as IDLE, LISTENING, THINKING, SPEAKING, and ERROR.
3. Connect those states to actual ARIA events instead of pretending the system has feelings.
4. Later, if the hardware budget allows, reuse the same state model on a small robot display and ESP32-based body.

The current ARIA project remains a local-first assistant with an Android client and Python server. This image does not mean a humanoid body, autonomous movement, or a MIRA feature has been implemented.

## Safety and privacy

Keep owner authentication and the permission engine in ARIA's own code. Treat external agent frameworks and model/tool outputs as untrusted until reviewed. Require owner approval for sensitive actions, external messages, deployments, payments, and destructive changes.
