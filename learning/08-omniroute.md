# 08 - OmniRoute research

## Source reviewed

A user-provided screenshot describes an open-source tool named **OmniRoute** and mentions using it to connect coding tools such as Claude Code to multiple AI model providers.

The screenshot highlights:
- Claude Code as a coding/agent client
- Kimi and GLM models as examples of providers/models
- routing multiple AI providers through one gateway
- a community post with a large number of comments

## What was verified

The current OmniRoute GitHub documentation describes OmniRoute as a local/remote AI gateway that can expose an OpenAI-compatible endpoint and connect coding tools including Claude Code, Codex CLI, Gemini CLI, Cursor, Cline, OpenCode and others. It also documents provider connections, endpoints/API keys, fallback combinations, and remote mode. The exact provider/model catalog changes over time, so ARIA should query the live catalog rather than hard-code claims from a screenshot.

Useful documented pattern:

1. Run OmniRoute locally first.
2. Connect one or more providers.
3. Create a scoped endpoint/API key.
4. Point a coding client at the OmniRoute endpoint.
5. Use fallback/auto-routing when appropriate.
6. Keep ARIA's own permission engine in front of tools that can modify files, deploy software, spend money, or access sensitive data.

## ARIA integration decision

**Useful for ARIA:** YES, as an optional model gateway.

Proposed architecture:

ARIA Core -> Permission Engine -> OmniRoute -> selected AI provider/model

Local-first fallback remains:

ARIA Core -> Ollama/Qwen local

This means OmniRoute must not replace ARIA's owner authorization layer. It is an inference/routing component, not the owner.

## Security notes

- Do not put API keys, OAuth tokens, browser cookies, or session cookies in GitHub.
- Prefer scoped credentials.
- Treat remote OmniRoute endpoints as sensitive infrastructure.
- Do not automatically execute tool output from a model.
- Require ARIA owner approval for destructive, financial, credential, deployment, or external-message actions.
- Keep local Ollama available as an offline fallback.

## Next experiment

Before adding OmniRoute to production ARIA:

1. Install/test it locally on the laptop.
2. Connect a non-sensitive provider or local-compatible endpoint.
3. Verify one simple coding request.
4. Measure RAM/CPU usage on the current laptop.
5. Add an ARIA adapter only if it improves capability without weakening authorization.

### References

- OmniRoute project/documentation: https://github.com/ourines/omniroute
- OmniRoute README: https://github.com/ourines/omniroute/blob/main/README.md
- Claude Code integration guide: https://github.com/ourines/omniroute/blob/main/docs/guides/CLAUDE-CODE-CONFIGURATION.md
