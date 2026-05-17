# gtd-todoist

A GTD scaffold where AI agents reason about Todoist, while scheduled jobs only remind the user to start review flows.

<p>
  <img alt="GTD" src="https://img.shields.io/badge/method-GTD-0f766e?style=flat-square">
  <img alt="Todoist" src="https://img.shields.io/badge/tool-Todoist-dc2626?style=flat-square">
  <img alt="Reminder only" src="https://img.shields.io/badge/cron-reminder--only-2563eb?style=flat-square">
</p>

<!-- README-I18N:START -->
<p>
  <strong>English</strong> | <a href="./README.zh-CN.md">简体中文</a>
</p>
<!-- README-I18N:END -->

> [!IMPORTANT]
> Cron jobs in this scaffold do not mutate Todoist. They only remind the user to start a flow in the main chat session, where the agent proposes changes and waits for confirmation.

## What It Solves

Todoist automation is risky when task titles, labels, and due dates can be rewritten without review. This scaffold keeps the agent in the main conversation, uses stable task IDs for writes, and keeps cron as a reminder layer only.

## What's Included

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
| `gtd-weekly-review` | Run a weekly review across Get Clear, Get Current, and Get Creative. |
| `health-check` | Run a read-only audit of workspace files, skill contracts, runtime visibility, and reminder-only cron. |

## Quick Start

1. Read [`deployment-plan.md`](./deployment-plan.md).
2. Back up the current Todoist workspace.
3. Create or verify the projects, labels, and filters described in the plan.
4. Copy the three `skills/<name>/SKILL.md` files into the target agent workspace.
5. Append [`agents-section.md`](./agents-section.md) to the target `AGENTS.md` or equivalent router file.
6. Replace placeholder delivery values such as `<TELEGRAM_USER_ID>`, `<BOT_ACCOUNT>`, and timezone.
7. Add reminder-only cron jobs.
8. Run the health check before relying on the setup.

## Core Rules

- The main chat session owns execution and user confirmation.
- Cron reminders are isolated prompts, not automation authority.
- Todoist writes must use stable task IDs or Todoist URLs, not task titles.
- `td task update --labels` replaces labels, so agents must read and merge existing labels before writing.
- Destructive or batch actions require explicit item-by-item approval.

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
