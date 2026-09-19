# 02 - ARIA Architecture

## First milestone

The project is now designed as a **local-first** assistant.

### Key idea

Internet is an accelerator, not the foundation.

- Without internet: local Qwen + local memory + local tools can still work.
- With internet: ARIA can later use a server and web-connected tools.
- With server + internet: a larger model can be used when the laptop cannot handle it.

### Protection

The assistant is not designed to blindly execute every instruction. Sensitive actions will pass through an approval layer.

### Next coding milestone

Build the Android companion and the permission engine after the local core is tested.
