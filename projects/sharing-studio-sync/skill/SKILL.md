---
name: sharing-studio-sync
description: Synchronize this public sharing-studio repository with Kevin's current local source-of-truth scaffolds for L1 memory, L2 Second Brain, GTD Todoist, and heavy agent workflows; use when the user asks to update, sync, publish, or push sharing-studio from the latest local runtime state.
---

# sharing-studio-sync

Synchronize `sharing-studio` from private/local source-of-truth scaffolds into a public, redacted GitHub-ready repository.

## Trigger

Use this Skill when the user asks to sync or publish `sharing-studio`, update it from local runtime state, or push the latest scaffolds to GitHub.

## Core Rule

This Skill is not a blind copy operation. It is a publish pipeline:

```
discover truth -> compare public repo -> update redacted scaffold -> scan -> review diff -> user approval -> commit/push
```

Never publish private content, credentials, runtime state, local planning files, ByteRover data, real notes, or real Todoist tasks.

## Source-of-Truth Map

Treat these local locations as latest runtime state:

| Domain | Source of truth | Public target |
|---|---|---|
| L1 agent memory | `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, public-safe global settings examples | `projects/agent-memory-stack/` |
| L2 Second Brain | `<vault-path>\CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.claude/skills/`, `.claude/scripts/`, `.obsidian/` portable config | `projects/second-brain-scaffold/` |
| GTD Todoist | Public scaffold files in `projects/gtd-todoist/` plus any user-provided current workspace scaffold path | `projects/gtd-todoist/` |
| Agent workflows | `~/.agents/skills/heavy-research/`, `~/.agents/skills/heavy-review/` | `projects/agent-workflows/` |
| Sync workflow | Public distributable Skill copy plus local runtime mirrors | `projects/sharing-studio-sync/skill/`; repo-root `.claude/skills/sharing-studio-sync/`, `.agents/skills/sharing-studio-sync/`, and `.gemini/skills/sharing-studio-sync/` are local runtime mirrors only |

If a source path is missing, report it and continue with the other domains. Do not invent current state.

## Publish Boundaries

Always exclude:

- Real `wiki/`, `daily/`, `raw/`, `index.md`, task data, personal notes, or Todoist content.
- Repo-root agent state and config: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.claude/`, `.agents/`, `.codex/`, `.gemini/`.
- Runtime/session files: `task_plan.md`, `progress.md`, `findings.md`, `.workflows/`, `.brv/`, `.brv`.
- Secrets and auth state: `.env`, `auth.json`, `oauth_creds.json`, API keys, provider configs, webhook URLs, cookies, tokens, installation IDs, account IDs.
- Machine-specific absolute paths except sanitized placeholders such as `<vault-path>` or `<agent-workspace>`.

Repository-local agent files may be tracked locally in this repo, but must not be pushed if they match the global protected-path policy. Public scaffold directories under `projects/` are separate and may be published after scanning. Before any push, inspect the outgoing commit range.

## Workflow

### S0. Preflight

1. Confirm CWD is the `sharing-studio` repository root.
2. Run `git status --short` and identify existing user changes.
3. Read root `AGENTS.md` / `CLAUDE.md` if present. Keep their H1-differentiated sync rule.
4. Run the bundled `scripts/preflight-sharing-studio-sync.ps1` if available from the active Skill directory or `projects/sharing-studio-sync/skill/scripts/`.
5. If there are unrelated dirty changes, do not overwrite them. Work around them or ask.

### S1. Discover Current Truth

Read only the files needed for the requested sync scope. For a full sync, inspect:

- L1: three global router files and public-safe settings examples.
- L2: vault router files, local vault skills, deterministic scripts, `.obsidian` portable config, MCP example.
- GTD: current scaffold files and any user-provided runtime scaffold.
- Agent workflows: `heavy-research` and `heavy-review` Skill directories.

For each domain, build a small manifest:

```markdown
domain:
source_paths:
target_paths:
public_safe_files:
excluded_private_files:
status_delta:
```

### S2. Update Public Targets

Update public targets conservatively:

- Copy or rewrite only public-safe scaffold files.
- For global/user paths, replace usernames and absolute machine paths with placeholders.
- For `agent-workflows`, include the current `heavy-research` and `heavy-review` Skill files under `projects/agent-workflows/skills/`.
- For this Skill, update the public copy under `projects/sharing-studio-sync/skill/`, then mirror it to the three repo-root runtime copies. Never stage those repo-root runtime copies for remote push.
- Update project README files so status reflects the current implementation.
- Update root README / README.zh-CN.md project table and layout when projects are added or status changes.

Use structured parsing or direct file copying where practical. Do not do lossy ad hoc edits to JSON; validate JSON after edits.

### S3. Scan

Run these checks before asking for approval:

1. `git diff --stat`
2. Secret and private-path scan over changed files.
3. Protected push path scan for staged files and outgoing commits.
4. JSON / PowerShell parser checks for changed `.json` / `.ps1`.
5. README link/path sanity check for changed markdown.

At minimum, scan for secret-like tokens, account credentials, and machine-specific path literals. The scan should cover:

```text
AKIA|AIza|sk-|xoxb-|ghp_|github_pat_|Bearer\s+[A-Za-z0-9._-]+
oauth|refresh_token|access_token|api[_-]?key|secret|password|private key
TELEGRAM_USER_ID=[0-9]|BOT_TOKEN|webhook
```

Also scan for literal local user-profile paths and literal cloud-drive vault paths. Public scaffolds should use placeholders such as `<home>`, `<vault-path>`, and `<TELEGRAM_USER_ID>`.

### S4. User Review Gate

Before commit or push, report:

- Domains synced.
- Files changed.
- Files intentionally excluded.
- Scan results.
- Any residual risks or manual checks.

Ask for explicit approval before commit/push unless the user already clearly requested commit and push after sync and all scans are clean. If scans fail, do not commit/push.

### S5. Commit And Push

Only after approval and clean scans:

1. Stage only public-safe files. Never stage repo-root `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.claude/`, `.agents/`, `.codex/`, `.gemini/`, `.workflows/`, `.brv/`, or PWF files.
2. Re-run protected path check on staged files.
3. Commit with a concise message, e.g. `Update sharing-studio scaffolds`.
4. Before `git push`, inspect outgoing commit range and block if protected paths are included.
5. Push to the configured GitHub remote.

## Notes

- GitHub secret scanning and push protection are useful final safety nets, not a substitute for local scanning.
- `.gitignore` prevents new untracked files from being added accidentally, but it does not protect files already tracked or already committed.
- If a project has a real runtime source that cannot be safely inspected or is not discoverable, record it as "source unavailable" instead of guessing.
