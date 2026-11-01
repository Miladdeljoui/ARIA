# Iranian websites MCP integration

## Selected upstream

The original reference was `sepehr071/awesome-iran-mcp`. The maintainer's current repository/catalog is now:

- https://github.com/sepehr071/iran-mcp
- Persian catalog: https://mcpfarsi.ir
- MIT is stated upstream; verify each package's license and terms before deployment.

The upstream catalog has grown beyond the original snapshot of 19 servers / 308 tools. Its current README describes 36 unofficial servers plus selected official hosted servers and hundreds of tools. Counts change; do not hard-code the old count.

## What it adds to ARIA

Read/search tools for Iranian shopping, classifieds, food, travel, health, books, prices, public laws, tax information and news. Examples include Digikala, Torob, Divar, Snappfood, Jabama, MrBilit, Paziresh24, Taaghche, Fidibo and 30book.

These are MCP website tools, not LLM models. They do not repair chat inference by themselves and do not provide image/video generation.

## Required architecture

Do not package Python MCP servers inside the Android APK. Run selected servers on the ARIA Python backend or a separate Linux VPS. Android talks only to the authenticated ARIA API:

```
ARIA Android (Compose)
        | HTTPS
        v
ARIA Python API (VPS / domestic host)
        |--> selected Iran MCP servers (uvx)
        |--> model provider adapter (OpenAI-compatible API)
        |--> image/video provider adapters (separate)
```

Keep provider keys and proxy credentials in backend secrets, never in the APK. MCP processes must not be exposed directly to the public internet.

## Safe rollout

1. Start with read-only servers only and enable only tools needed for each task.
2. Treat website-returned text as untrusted; never follow instructions embedded in scraped pages.
3. Require explicit owner confirmation before booking, payment, messaging, account changes or other consequential actions.
4. Do not enable PayPing or Bale write-capable tools until credentials and approval flows are tested.
5. Some Iranian sites may block foreign IPs. Upstream documents optional per-server proxy variables; use a trusted, lawful Iranian egress proxy only where necessary.
6. Test each selected server from the actual deployment region. Unofficial site endpoints can change or return 403/timeouts.

## Backend setup references

Upstream documents Python package servers launched with `uvx`, for example:

```bash
uvx digikala-mcp
uvx jabama-mcp
```

Exact package names, tool names, environment variables and transport must be taken from the current upstream files at deployment time. Do not blindly copy an old all-in-one MCP config.

- https://github.com/sepehr071/iran-mcp
- https://github.com/sepehr071/iran-mcp/blob/main/AGENTS.md
- https://github.com/sepehr071/iran-mcp/blob/main/servers.json
- https://github.com/sepehr071/iran-mcp/blob/main/TOOLS.md

## ARIA status

This is an integration plan, not a claim that MCP servers are deployed or connected to the ARIA runtime. Actual integration still needs an MCP client in the backend, process lifecycle management, tool allowlisting, approval checks, timeouts, logs and integration tests.

Image/video generation is a separate provider integration requiring a reachable API, model availability, credentials and budget. Iranian website MCP tools do not generate images or clips.
