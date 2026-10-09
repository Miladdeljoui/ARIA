# Agency Agents: Specialist Prompt Library

Source repository: https://github.com/msitarzewski/agency-agents

## What it is

Agency Agents is an open-source collection of role-specific AI agent definitions. Each specialist typically describes a mission, working style, process, and expected deliverables. Examples cover software engineering, design, research, marketing, product work, and security review.

The repository is best understood as a library of specialist instructions, not a complete autonomous multi-agent runtime. A persona can guide a compatible AI coding tool, but it does not by itself provide model hosting, persistent memory, safe tool execution, orchestration, or permissions.

## How ARIA could use it

Treat the collection as inspiration for ARIA's own small, reviewed specialist profiles:

- Research Analyst: gather sources, compare claims, and report uncertainty.
- Software Engineer: propose focused code changes and tests.
- Security Reviewer: inspect ARIA defensively and recommend fixes.
- Product Planner: turn ideas into small, testable milestones.
- Content Assistant: draft posts for review before publication.

Start with one specialist at a time and adapt only the relevant instructions. Keep the existing local Ollama model as the default so the feature does not require a larger model or paid service.

## Proposed ARIA flow

1. ARIA Core selects a specialist profile for the task.
2. The specialist produces a plan or proposed output.
3. The Permission Engine classifies the requested action.
4. Read-only, low-risk work can proceed within configured limits.
5. External messages, file deletion, credential changes, deployments, payments, or other sensitive actions require explicit owner approval.
6. Record the result and test changes before accepting them.

A specialist prompt is not a security boundary. Enforce permissions in code, validate tool inputs, and treat model/tool output as untrusted.

## Adoption checklist

- Review the upstream README, current files, license, and update history before importing anything.
- Keep copied/adapted material attributed and comply with its license.
- Do not install scripts or grant broad filesystem, shell, browser, or account access without inspection.
- Never expose passwords, API keys, cookies, or private ARIA memory to a specialist prompt or public repository.
- Test with harmless sample tasks first; retain a rollback path.

## Status

This is a documented integration proposal. It does not mean the upstream agents have been installed in ARIA, and no agent execution or end-to-end test is claimed by this document.

## Links

- Upstream project: https://github.com/msitarzewski/agency-agents
- ARIA project: https://github.com/Miladdeljoui/ARIA
