# sharing-studio-sync

A repository sync workflow for publishing Kevin's current local agent scaffolds into this public `sharing-studio` hub.

> [!WARNING]
> This project is a publication workflow, not a backup tool. It must never publish private notes, real Todoist tasks, credentials, runtime state, or local planning files.

## What It Provides

```text
sharing-studio-sync/
└── skill/
    ├── SKILL.md
    └── scripts/
        └── preflight-sharing-studio-sync.ps1
```

The Skill keeps public scaffolds aligned with local source-of-truth systems:

| Domain | Public target |
| :--- | :--- |
| L1 memory rules | `projects/agent-memory-stack/` |
| L2 Second Brain scaffold | `projects/second-brain-scaffold/` |
| GTD Todoist harness | `projects/gtd-todoist/` |
| Heavy research/review workflows | `projects/agent-workflows/` |

## Workflow

1. Discover local source-of-truth files.
2. Compare them with the public scaffold copies in this repo.
3. Copy or rewrite only public-safe scaffold files.
4. Replace private paths and account details with placeholders.
5. Run secret, path, parser, and protected-push checks.
6. Ask for user review before commit and push.

## Privacy Boundary

Do not publish:

- Real `wiki/`, `daily/`, `raw/`, `index.md`, or personal vault content.
- Todoist task titles, activity logs, account IDs, tokens, or webhook targets.
- `task_plan.md`, `progress.md`, `findings.md`, `.workflows/`, `.brv/`, or runtime agent state.
- Repo-root `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.claude/`, `.agents/`, `.codex/`, and `.gemini/`.
- Local absolute paths such as real user profiles or cloud-drive locations.

Use placeholders such as `<vault-path>`, `<agent-workspace>`, `<TELEGRAM_USER_ID>`, and `<BOT_ACCOUNT>` instead.
