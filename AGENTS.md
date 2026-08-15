# Repository Agent Markdown

## Repository Scope

* This repository is my personal AI usage ecosystem. It stores the desensitized mirrors of my global agent markdown and the authoritative copies of my global agent skills.
* This repository is public. Do not commit secrets, API keys, private vault content, local credentials, or machine-specific absolute paths. Global rule mirrors keep `<second-brain-path>` / `<your-username>` placeholders.
* Follow the global agent markdown first; this file only adds repository-local constraints.

## Repository Layout

* `global/` — desensitized mirrors of the global `CLAUDE.md` / `AGENTS.md` / `AGENTS.dsh.md` rule files. The three files must stay byte-identical and share the H1 `# Global Agent Markdown`.
* `skills/` — authoritative copies of the global skills installed under the local global skills directory. Claude Code reuses the same entities via symlinks.
* Repository-root `AGENTS.md` / `CLAUDE.md` are tracked, public-safe repository rules.
* PWF files `task_plan.md`, `progress.md`, and `findings.md` are repository task memory.

## Sync Conventions

* When a global skill changes locally, update its `skills/` copy here and commit it.
* When the global rule files change locally, update the desensitized mirrors in `global/` and commit them.
* Never write machine-specific paths, usernames, or credentials into tracked files.
