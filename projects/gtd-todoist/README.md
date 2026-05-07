# gtd-todoist

A GTD harness for AI agents that manage Todoist through a CLI while cron only sends reminders.

> [!IMPORTANT]
> Cron jobs in this scaffold do not mutate Todoist. They only remind the user to start a flow in the main chat session, where the agent proposes changes and waits for confirmation.

## What It Provides

```text
gtd-todoist/
├── deployment-plan.md              # Todoist scaffold and cron setup
├── agents-section.md               # router section for an agent workspace
├── skills/
│   ├── gtd-inbox-triage/
│   ├── gtd-daily-review/
│   └── gtd-weekly-review/
└── health-check/
    ├── SKILL.md
    └── scripts/
```

## Skills

| Skill | Purpose |
| :--- | :--- |
| `gtd-inbox-triage` | Clarify Inbox items and route them to next action, waiting, project, someday, or done. |
| `gtd-daily-review` | Review today's completed, unfinished, overdue, Inbox, and tomorrow items. |
| `gtd-weekly-review` | Run a GTD weekly review across Get Clear, Get Current, and Get Creative. |
| `health-check` | Read-only audit of workspace files, skill contracts, runtime visibility, and reminder-only cron. |

## Core Rules

- The main chat session owns all execution and user confirmation.
- Cron reminders are isolated prompts, not automation authority.
- Todoist writes must use stable task IDs or Todoist URLs, not task titles.
- `td task update --labels` replaces labels, so agents must read and merge existing labels before writing.
- Destructive or batch actions require explicit item-by-item approval.

## Quick Start

1. Read [`deployment-plan.md`](./deployment-plan.md).
2. Back up the current Todoist workspace.
3. Create or verify the projects, labels, and filters described in the plan.
4. Copy the three `skills/<name>/SKILL.md` files into the target agent workspace.
5. Append [`agents-section.md`](./agents-section.md) to the target `AGENTS.md` or equivalent router file.
6. Replace placeholder delivery values such as `<TELEGRAM_USER_ID>`, `<BOT_ACCOUNT>`, and timezone.
7. Add the reminder-only cron jobs.
8. Run the health check before relying on the setup.

## Dependencies

- Todoist account and API access.
- A Todoist CLI such as `td`, or an equivalent wrapper with project, label, filter, task, completed, upcoming, and activity commands.
- An agent runtime that can load markdown-defined skills.
- A cron or scheduler layer that can send reminders to the main user channel.

## Privacy Boundary

Do not publish:

- Todoist API tokens.
- Real task titles, project data, labels, activity logs, or account IDs.
- Real chat delivery IDs, bot accounts, webhook URLs, or scheduler state.
- Machine-specific hostnames, SSH targets, or private IP addresses.
