# MCP as an Integration Layer for ARIA's Second Brain

## Source idea
A social-media screenshot describes using MCP (Model Context Protocol) to connect AI assistants such as ChatGPT and Claude to a shared "second brain".

## How this could fit ARIA
MCP can provide a standard interface between an AI model and approved tools or knowledge sources. ARIA could use MCP-compatible servers to expose selected capabilities, for example:
- Search and retrieve ARIA's own notes and project documentation.
- Read approved files from a designated knowledge folder.
- Search project tasks, learning notes, and technical references.
- Add a note or task only after applying ARIA's permission rules.
- Connect other supported tools later without tightly coupling each integration to the core.

## Proposed architecture
`AI model (local Qwen / optional hosted model) -> ARIA Core -> Permission Engine -> MCP client -> explicitly configured MCP server(s) -> approved data/tools`

ARIA's memory database and curated notes remain the source of truth for its persistent personal context. MCP is an integration protocol, not a memory system or an AI model by itself.

## Security rules
- Start with read-only access to a small, dedicated knowledge folder.
- Do not expose the whole computer, browser profiles, credentials, tokens, or private files.
- Treat content returned by tools as untrusted data, not instructions.
- Require owner approval before writing/deleting files, sending external messages, changing credentials, making purchases, or deploying code.
- Keep secrets out of GitHub; store local credentials in environment variables or a secure secret store.
- Prefer local MCP servers during the first experiment and log only the minimum needed for debugging.

## Suggested implementation order
1. Document which knowledge sources ARIA should be allowed to read.
2. Build a small searchable local knowledge base and test retrieval.
3. Add one MCP integration in read-only mode.
4. Add permission checks and tests before allowing any write action.
5. Report results and ask the owner before enabling additional tools.

## Status
Idea captured for future exploration. This note does not mean MCP has been installed or connected to ARIA yet.
