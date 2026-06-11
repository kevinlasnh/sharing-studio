# second-brain-scaffold

An Obsidian and Basic Memory vault scaffold for AI-assisted ingest, query, lint, graph maintenance, and daily journaling.

<p>
  <img alt="Obsidian" src="https://img.shields.io/badge/Obsidian-vault-7c3aed?style=flat-square">
  <img alt="Basic Memory" src="https://img.shields.io/badge/Basic%20Memory-MCP-0f766e?style=flat-square">
  <img alt="No real notes" src="https://img.shields.io/badge/content-scaffold--only-2563eb?style=flat-square">
</p>

<!-- README-I18N:START -->
<p>
  <strong>English</strong> | <a href="./README.zh-CN.md">简体中文</a>
</p>
<!-- README-I18N:END -->

> [!WARNING]
> This directory is a scaffold, not a vault backup. It intentionally contains no real `wiki/`, `daily/`, `raw/`, or personal `index.md` content.

## What It Solves

Long-running personal knowledge systems need stronger boundaries than a folder full of notes. This scaffold separates raw evidence, durable wiki pages, daily logs, graph configuration, deletion workflows, backup closure, and agent write permissions.

## What's Included

```text
second-brain-scaffold/
├── CLAUDE.md                       # L2 vault router for Claude Code
├── AGENTS.md                       # L2 vault router for Codex
├── GEMINI.md                       # L2 vault router for Gemini CLI
├── .claude/
│   ├── settings.json               # vault-level hooks
│   ├── scripts/                    # deterministic PowerShell guardrails
│   └── skills/                     # Claude Code local Second Brain skills
├── .agents/
│   └── skills/                     # Codex / cross-agent local skill mirror
├── .gemini/
│   └── skills/                     # Gemini CLI local skill mirror
├── .obsidian/                      # portable Obsidian configuration
└── mcp/
    └── basic-memory-mcp.example.json
```

## Skills

| Skill | Purpose |
| :--- | :--- |
| `second-brain-ingest` | Route source material into durable `wiki/` pages after search-before-write. |
| `second-brain-delete` | Plan, confirm, apply, and validate safe deletes for explicit wiki, raw, daily, domain, or old workflow targets. |
| `second-brain-query` | Run read-only lookup across the structured vault. |
| `second-brain-lint` | Audit links, frontmatter, index coverage, raw boundaries, and graph health. |
| `second-brain-journal` | Write `daily/YYYY-MM-DD.md` entries outside the concept graph, then close Basic Memory sync and backup handoff. |
| `second-brain-hf-backup` | Push a full private vault Git snapshot to a configured Hugging Face dataset remote after journal closure. |
| `second-brain-graph-manager` | Maintain graph color groups and image-display CSS. |
| `second-brain-vault-audit` | Check router, hooks, skills, MCP, Obsidian, and Basic Memory wiring. |

## Quick Start

1. Create a new Obsidian vault at your preferred local or synced path.
2. Copy `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.claude/`, `.agents/`, `.gemini/`, and `.obsidian/` into the vault root.
3. Register Basic Memory for the vault:

   ```powershell
   basic-memory project add second-brain "<vault-path>" --default --local
   ```

4. Add the MCP registration from [`mcp/basic-memory-mcp.example.json`](./mcp/basic-memory-mcp.example.json) to your agent runtime.
5. If you use the Hugging Face backup workflow, replace `<hf-private-dataset-url>` in the scaffold with your private dataset remote.
6. Open the vault in Obsidian once so local plugin settings initialize.
7. Run `second-brain-vault-audit` before using the vault for real content.

## Guardrails

- `wiki-path-policy.ps1` blocks legacy or unsupported wiki paths.
- `shell-write-policy.ps1` blocks shell writes that bypass the vault's file policies.
- `wiki-prewrite-syntax-check.ps1` and `wiki-syntax-check.ps1` enforce Obsidian Markdown contracts.
- `wiki-write-reminder.ps1` reminds agents to search before writing and complete domain routing.
- `daily-no-link-policy.ps1` keeps daily notes out of the concept graph.
- `raw-link-policy.ps1` keeps source material as evidence, not navigation.

## Core Rules

- `wiki/` is the durable knowledge graph.
- `raw/` stores evidence and imported source material only.
- `daily/` stores chronological notes and should not link into the concept graph.
- Search-before-write is mandatory before creating or updating knowledge pages.
- High-risk structural edits go through proposal and confirmation gates: new domains, renames, moves, deletes, and merges.
- Journal closure owns the final Basic Memory reindex checkpoint and can hand off to a private Hugging Face backup.

## Dependencies

- [Obsidian](https://obsidian.md/) 1.12+.
- [Basic Memory](https://github.com/basicmachines-co/basic-memory), recommended for MCP-backed indexing.
- An agent runtime that can load the vault-level router and local skills.
- Optional Obsidian community plugin `realclaudian` / Claudian if you want embedded agent tabs; the plugin package and runtime state are not included here.
- Optional cloud sync such as Obsidian Sync, iCloud, Google Drive, or another provider.

## Privacy Boundary

Do not publish:

- Real notes from `wiki/`, `daily/`, or `raw/`.
- Obsidian `workspace*.json` files.
- Basic Memory databases or project state.
- Private backup remote URLs.
- Real vault paths, account identifiers, API keys, or local machine paths.
