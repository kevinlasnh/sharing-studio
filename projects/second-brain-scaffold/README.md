# second-brain-scaffold

An Obsidian + Basic Memory vault scaffold for AI-assisted ingest, query, lint, and daily journaling.

> [!WARNING]
> This directory is a scaffold, not a vault backup. It intentionally contains no real `wiki/`, `daily/`, `raw/`, or personal `index.md` content.

## What It Provides

```text
second-brain-scaffold/
├── CLAUDE.md                       # L2 vault router for Claude Code
├── AGENTS.md                       # L2 vault router for Codex
├── .claude/
│   ├── settings.json               # vault-level hooks
│   ├── scripts/                    # deterministic PowerShell guardrails
│   └── skills/                     # local Second Brain skills
├── .obsidian/                      # portable Obsidian configuration
└── mcp/
    └── basic-memory-mcp.example.json
```

## Skills

| Skill | Purpose |
| :--- | :--- |
| `second-brain-ingest` | Route source material into durable `wiki/` pages after search-before-write. |
| `second-brain-query` | Read-only lookup across the structured vault. |
| `second-brain-lint` | Audit links, frontmatter, index coverage, raw boundaries, and graph health. |
| `second-brain-journal` | Write `daily/YYYY-MM-DD.md` entries outside the concept graph. |
| `second-brain-graph-manager` | Maintain graph color groups and image-display CSS. |
| `second-brain-vault-audit` | Check router, hooks, skills, MCP, Obsidian, and Basic Memory wiring. |

## Guardrails

- `wiki-path-policy.ps1` blocks legacy or unsupported wiki paths.
- `wiki-prewrite-syntax-check.ps1` and `wiki-syntax-check.ps1` enforce Obsidian Markdown contracts.
- `wiki-write-reminder.ps1` reminds agents to search before writing and complete domain routing.
- `daily-no-link-policy.ps1` keeps daily notes out of the concept graph.
- `raw-link-policy.ps1` keeps source material as evidence, not navigation.

## Quick Start

1. Create a new Obsidian vault at your preferred local or synced path.
2. Copy `CLAUDE.md`, `AGENTS.md`, `.claude/`, and `.obsidian/` into the vault root.
3. Register Basic Memory for the vault:

   ```powershell
   basic-memory project add second-brain "<vault-path>" --default --local
   ```

4. Add the MCP registration from [`mcp/basic-memory-mcp.example.json`](./mcp/basic-memory-mcp.example.json) to your agent runtime.
5. Open the vault in Obsidian once so local plugin settings initialize.
6. Run `second-brain-vault-audit` before using the vault for real content.

## Core Rules

- `wiki/` is the durable knowledge graph.
- `raw/` stores evidence and imported source material only.
- `daily/` stores chronological notes and should not link into the concept graph.
- Search-before-write is mandatory before creating or updating knowledge pages.
- High-risk structural edits go through pending review: new domains, renames, moves, deletes, and merges.

## Dependencies

- [Obsidian](https://obsidian.md/) 1.12+.
- [Basic Memory](https://github.com/basicmachines-co/basic-memory), recommended for MCP-backed indexing.
- Claude Code plugins compatible with the local skills referenced by the router.
- Optional cloud sync such as Obsidian Sync, iCloud, Google Drive, or another provider.

## Privacy Boundary

Do not publish:

- Real notes from `wiki/`, `daily/`, or `raw/`.
- Obsidian `workspace*.json` files.
- Basic Memory databases or project state.
- Real vault paths, account identifiers, API keys, or local machine paths.
