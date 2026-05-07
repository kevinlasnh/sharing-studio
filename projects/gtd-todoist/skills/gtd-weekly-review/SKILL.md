---
name: gtd-weekly-review
description: GTD Weekly Review for Todoist. Use when the user says "开始 Weekly Review", "做周回顾", "开始周回顾", or wants a weekly GTD system review. Guides Get Clear, Get Current, and Get Creative step by step, waiting for user confirmation at every step.
---

# GTD Weekly Review

## Ground Rules

- Work in the main conversation session; the Sunday cron only reminds the user.
- Proceed step by step and wait for the user before moving to the next step.
- Do not delete projects, delete tasks, or change Horizons without explicit confirmation.
- Use `id:<task_id>` or Todoist URLs for all mutating commands.
- Do not rely on task titles for destructive or bulk changes.

## Preflight

Run:

```bash
td inbox --json --full
td project list --json --full
td label list --json --full
td filter list --json --full
```

If Inbox is not empty, recommend running `gtd-inbox-triage` first.

## Weekly Review Steps

### 1. Get Clear: Capture Loose Ends

Ask the user whether anything is still in their head, notes, chats, or calendar that should be captured. Add confirmed items to Inbox:

```bash
td task quickadd "Captured item text"
```

### 2. Get Current: Review Completed Work

```bash
td completed list --since 7d --json --full
```

Summarize completed tasks by project and identify meaningful wins.

### 3. Get Current: Calendar / Activity Follow-up

```bash
td activity --since 7d --json --full
```

Ask whether any meetings, messages, or events created follow-up tasks.

### 4. Get Current: Project Health

For each active project:

```bash
td task list --project "Project Name" --json --full
```

Check:

- Is the outcome still wanted?
- Is there at least one clear `next` action?
- Are there stale overdue tasks?
- Should anything move to Someday / Maybe?
- Should the project be split, merged, or archived?

Ask before changing anything.

### 5. Get Current: Waiting For / Someday

```bash
td task list --label "waiting" --json --full
td task list --project "🗂 Someday / Maybe" --json --full
```

Check whether to follow up, reactivate, keep, or cancel items.

### 6. Get Current: Horizons Alignment

```bash
td task list --project "🌅 Horizons" --json --full
```

For each long-term goal, discuss whether current projects still serve it. Do not change Horizons unless the user explicitly instructs it.

### 7. Get Creative

Ask:

- What new idea, goal, or project is worth capturing?
- What has been avoided but still matters?
- What would make next week easier?

Capture confirmed ideas to Inbox or a specific project.

### 8. Engage: Next Week Preview

```bash
td upcoming 7 --json --full
td task list --filter "overdue" --json --full
```

Suggest:

- hard deadlines
- 3-5 project focus areas
- Monday MIT candidates

Wait for confirmation before changing priorities or dates.

## Closing Report

End with:

- Inbox status
- active project count
- overdue count
- waiting count
- Someday count
- suggested focus for next week

Do not use Markdown tables in Telegram output.
