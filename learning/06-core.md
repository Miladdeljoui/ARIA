# 06 - ARIA Core: Memory + Permissions

## Built

- persistent SQLite memory
- conversation history
- deterministic permission levels
- online/local runtime selector

## Permission levels

- safe
- approval
- critical

The classifier is intentionally conservative and does not execute actions. It provides the decision that a future tool runner can use.

## Portfolio skills

- Python dataclasses and enums
- SQLite persistence
- locking for local state
- API architecture
- offline-first design
- security-oriented authorization boundaries

## Next

Connect the permission engine to a tool registry, then add voice input/output and Android online/local fallback.
